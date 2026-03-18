"""
脚本：phase2_generate_log_chunk.py

与 phase2_extract_qa_from_md、phase2_generate_for_chunking_json 同属「生成」阶段：从已有结构化数据生成
供 phase3 向量化使用的 QA 与语义分块，不做向量化本身。

使用 LLM 从故障窗口日志片段生成「故障描述-日志片段」QA 对与日志摘要，输出到 qa_pair 与 semantic_chunk，
供 phase3_text_QA_vectorize 读取并写入 ChromaDB。

处理逻辑：
- 输入：data_prepare/log_cache/fault_index.json 及其中引用的 fault_windows 索引与 *_window_*.jsonl 片段。
- 对每个故障窗口片段：
  1. 将 jsonl 格式化为「[时间] 模块 级别: 消息」的连续文本；
  2. 调用 AWS Bedrock Claude，用两个独立 prompt 生成：
     a) **故障描述-日志证据 QA 对**：问题为自然语言故障现象/用户问法，答案为从片段提炼的关键日志证据（2～5 条关键行或 1～2 句结论）；
     b) **日志摘要**：2～5 句摘要，含故障类型、涉及模块、时间范围、关键错误信息。
- 输出：
  - qa_pair/<source_stem>_log_qa.json：与 phase2 产出的 _qa.json 同结构（qa_pairs + metadata），供 phase3 一并向量化；
  - semantic_chunk/<source_stem>_log_for_chunking.json：与 phase2 产出的 _for_chunking.json 同结构（chunks 每条 content=摘要、metadata 含 case_id/device_sn/segment 等），供 phase3 一并向量化。
- 按 fault_windows 文件（即按源 log 的 source_stem）聚合：同一 log 的多个窗口片段合并为一份 _log_qa.json 与一份 _log_for_chunking.json。
- 依赖：boto3、Bedrock 可用；需先运行 phase1_preprocess_log 生成 log_cache 与 fault_index。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from common_schema import build_asset_record, stable_version_from_mapping

import sys as _sys
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

_aws_cfg = {}
_chunk_log_cfg = {}
try:
    from pipeline_config_loader import load_config as _load_config
    _cfg = _load_config(ensure_dirs=True)
    _aws_cfg = _cfg.get("aws") or {}
    _chunk_log_cfg = _cfg.get("chunking_log") or {}
    DATA_PREPARE_DIR = Path(_cfg["input"]["raw_material"]).parent
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    LOG_CACHE_DIR = Path(_cfg["intermediate"]["log_cache"])
    QA_PAIR_DIR = Path(_cfg["intermediate"]["qa_pair"])
    SEMANTIC_CHUNK_DIR = Path(_cfg["intermediate"]["semantic_chunk"])
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    LOG_CACHE_DIR = PROCESSED_DATA_DIR / "log_cache"
    QA_PAIR_DIR = PROCESSED_DATA_DIR / "qa_pair"
    SEMANTIC_CHUNK_DIR = PROCESSED_DATA_DIR / "semantic_chunk"

BEDROCK_REGION = _aws_cfg.get("region", "us-west-2")
BEDROCK_MODEL_ID = _aws_cfg.get("bedrock_model", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
FAULT_INDEX_FILENAME = "fault_index.json"
MAX_LOG_CHARS_PER_SEGMENT = int(_chunk_log_cfg.get("max_log_chars_per_segment", 28000))
MAX_LOG_LINES_PER_SEGMENT = int(_chunk_log_cfg.get("max_log_lines_per_segment", 600))


# ---------------------------------------------------------------------------
# 业界主流最佳实践：QA 提取 Prompt（角色 + 任务 + 约束 + 输出格式，仅基于给定内容）
# 参考：RAG Q&A 提取需明确「仅用给定内容」「与原文语言一致」「结构化输出」以降低幻觉、提高检索匹配。
# ---------------------------------------------------------------------------
PROMPT_QA_TEMPLATE = """你是一名充电/能源设备故障诊断与日志分析专家。下面是一段来自故障时间窗口内的设备结构化日志（每行格式为 [时间] 模块 级别: 消息）。请**仅根据这段日志**生成 1～5 个「故障描述-日志证据」问答对，用于后续 RAG 检索：问题为自然语言的故障现象描述或用户可能提出的问法，答案为从本片段中提炼的**关键日志证据**（可摘录 2～5 条关键日志行，或 1～2 句精炼结论，必须与给定日志一致）。

要求：
1. 问题：从用户/运维视角描述故障现象或排查问题（如「电表通信失败时日志有什么表现」「TCU 与 CCU 通信异常对应的日志」），与日志内容直接相关。
2. 答案：仅使用上述日志中的信息，可摘录关键行或概括，不得编造时间、模块、错误码。
3. 语言与日志一致：日志主要为中文则用中文，主要为英文则用英文。
4. 每个问答对独立、可单独用于检索；category 固定为 "fault_log"，keywords 为 2～5 个关键词便于检索。

只输出一个 JSON 数组，不要 markdown 代码块包裹以外的任何解释。

```json
[
  {{"question": "问题文本", "answer": "答案/关键日志证据", "category": "fault_log", "keywords": ["关键词1", "关键词2"]}}
]
```

上下文（可选参考，不参与生成）：case_id={case_id}, device_sn={device_sn}, 时间范围 {start_ts}～{end_ts}

日志片段：
---
{log_text}
---
JSON 数组（仅此，无其他文字）："""


# ---------------------------------------------------------------------------
# 业界主流最佳实践：日志摘要 Prompt（角色 + 任务 + 要点 + 简短输出）
# 参考：日志摘要需明确「摘要什么」「输出长度与格式」，结构化日志优先提取故障类型、模块、时间、关键错误。
# ---------------------------------------------------------------------------
PROMPT_SUMMARY_TEMPLATE = """你是一名设备日志分析专家。请对下面这段故障时间窗口内的结构化日志做**2～5 句**的摘要，要求：

1. 说明故障类型或异常性质（如通信失败、超时、状态异常等）；
2. 涉及的主要模块/组件（如 TCU、CCU、电表、OCPP 等）；
3. 时间范围（起止时间）；
4. 关键错误信息或状态码（从日志中摘录，不编造）。

语言与日志一致（中文或英文）。只输出摘要正文，不要 JSON、不要标题、不要「摘要：」前缀。

日志片段：
---
{log_text}
---
摘要（2～5 句）："""


def _relpath(path: Path, base: Path) -> str:
    """返回 path 相对 base 的路径字符串；若不可相对则返回 path.name。"""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return path.name


def load_fault_index(base_dir: Path) -> Dict[str, Any]:
    """加载 fault_index.json。"""
    path = LOG_CACHE_DIR / FAULT_INDEX_FILENAME
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_fault_index_entries(fault_index: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    同时遍历 by_case_id / by_device_sn 并去重，避免遗漏只出现在 device 维度的条目。
    去重键优先使用 fault_windows_file。
    """
    merged: List[Dict[str, Any]] = []
    seen_fw: set[str] = set()
    for group_key in ("by_case_id", "by_device_sn"):
        grouped = fault_index.get(group_key) or {}
        for _k, entries in grouped.items():
            for entry in entries or []:
                fw_rel = (entry.get("fault_windows_file") or "").strip().replace("\\", "/")
                if not fw_rel or fw_rel in seen_fw:
                    continue
                seen_fw.add(fw_rel)
                merged.append(entry)
    return merged


def segment_paths_from_index(
    fault_index: Dict[str, Any], base_dir: Path
) -> List[Tuple[Path, Dict[str, Any], str, str, str]]:
    """
    从 fault_index 收集 (segment_path, win_meta, case_id, device_sn, source_stem)。
    路径均基于 base_dir（data_prepare）。
    """
    seen_segments: set = set()
    jobs: List[Tuple[Path, Dict[str, Any], str, str, str]] = []

    for entry in _iter_fault_index_entries(fault_index):
        fw_rel = (entry.get("fault_windows_file") or "").strip().replace("\\", "/")
        if not fw_rel:
            continue
        fw_path = base_dir / fw_rel
        if not fw_path.exists():
            continue
        try:
            fw_data = json.loads(fw_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠ 跳过损坏 fault_windows 索引: {fw_path} ({type(e).__name__})")
            continue
        source_stem = fw_data.get("source_stem") or fw_path.stem.replace("_fault_windows", "")
        case_id = (fw_data.get("case_id") or "").strip()
        device_sn = (fw_data.get("device_sn") or "").strip()
        knowledge_layer = (fw_data.get("asset_meta") or {}).get("knowledge_layer") or (entry.get("knowledge_layer") or "evidence")
        for win in fw_data.get("fault_windows") or []:
            seg_rel = (win.get("segment_jsonl") or "").strip().replace("\\", "/")
            if not seg_rel:
                continue
            seg_path = base_dir / seg_rel
            if str(seg_path) in seen_segments:
                continue
            seen_segments.add(str(seg_path))
            if not seg_path.exists():
                continue
            jobs.append((seg_path, {**win, "knowledge_layer": knowledge_layer}, case_id, device_sn, source_stem))
    return jobs


def load_segment_as_text(segment_path: Path, max_chars: int = MAX_LOG_CHARS_PER_SEGMENT, max_lines: int = MAX_LOG_LINES_PER_SEGMENT) -> str:
    """将 *_window_*.jsonl 读入并格式化为「[ts] module level: message」的文本。"""
    lines_out: List[str] = []
    n = 0
    total = 0
    with segment_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            if n > max_lines:
                lines_out.append("... (后续日志已截断)")
                break
            try:
                rec = json.loads(line)
                ts = rec.get("ts") or ""
                mod = rec.get("module") or ""
                lv = rec.get("level") or ""
                msg = (rec.get("message") or "").strip()
                parts = [f"[{ts}]", mod, lv + ":", msg]
                out_line = " ".join(parts)
            except Exception:
                out_line = line
            total += len(out_line) + 1
            if total > max_chars:
                lines_out.append(out_line)
                lines_out.append("... (后续日志已截断)")
                break
            lines_out.append(out_line)
    return "\n".join(lines_out)


def call_claude(bedrock_client, model_id: str, prompt: str, max_tokens: int = 8000, temperature: float = 0.2) -> Optional[str]:
    """调用 Bedrock Converse API。"""
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        return response["output"]["message"]["content"][0]["text"]
    except Exception as e:
        print(f"    ✗ Claude 调用失败: {e}")
        return None


def parse_qa_response(response: str) -> List[Dict[str, Any]]:
    """从 LLM 响应中解析 JSON 数组形式的 QA 对。"""
    if not response or not response.strip():
        return []
    json_str = response.strip()
    # 尝试去掉 markdown 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if m:
        json_str = m.group(1).strip()
    else:
        m = re.search(r"\[\s*\{[\s\S]*\}\s*\]", response)
        if m:
            json_str = m.group(0).strip()
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def normalize_qa_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """标准化并校验 QA 项，确保下游 phase3_text_QA_vectorize 可直接消费。"""
    if not isinstance(item, dict):
        return None
    question = str(item.get("question", "")).strip()
    answer = str(item.get("answer", "")).strip()
    if not question or not answer:
        return None
    category = str(item.get("category", "fault_log")).strip() or "fault_log"
    raw_keywords = item.get("keywords", [])
    if isinstance(raw_keywords, list):
        keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
    else:
        kw = str(raw_keywords).strip()
        keywords = [kw] if kw else []
    return {
        "question": question,
        "answer": answer,
        "category": category,
        "keywords": keywords,
    }


def generate_qa_for_segment(
    bedrock_client,
    model_id: str,
    log_text: str,
    case_id: str,
    device_sn: str,
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """对一段日志文本调用 LLM 生成 QA 对。"""
    prompt = PROMPT_QA_TEMPLATE.format(
        case_id=case_id or "N/A",
        device_sn=device_sn or "N/A",
        start_ts=start_ts or "N/A",
        end_ts=end_ts or "N/A",
        log_text=log_text[:MAX_LOG_CHARS_PER_SEGMENT],
    )
    out = call_claude(bedrock_client, model_id, prompt, max_tokens=4096, temperature=0.2)
    return parse_qa_response(out) if out else []


def generate_summary_for_segment(
    bedrock_client,
    model_id: str,
    log_text: str,
) -> str:
    """对一段日志文本调用 LLM 生成摘要。"""
    prompt = PROMPT_SUMMARY_TEMPLATE.format(log_text=log_text[:MAX_LOG_CHARS_PER_SEGMENT])
    out = call_claude(bedrock_client, model_id, prompt, max_tokens=1024, temperature=0.2)
    if not out:
        return ""
    return out.strip()


def main():
    parser = argparse.ArgumentParser(
        description="从 log_cache 故障窗口片段生成 (故障描述-日志片段) QA 与日志摘要，写入 qa_pair 与 semantic_chunk"
    )
    parser.add_argument("--file", "-f", type=str, default=None, help="仅处理包含此名称的 segment（模糊匹配 segment 路径）")
    parser.add_argument("--dry-run", action="store_true", help="只列待处理片段，不调用 LLM、不写文件")
    parser.add_argument("--max-segments", type=int, default=None, help="最多处理多少个片段（用于试跑）")
    args = parser.parse_args()

    base_dir = DATA_PREPARE_DIR
    fault_index = load_fault_index(base_dir)
    if not fault_index or not (fault_index.get("by_case_id") or fault_index.get("by_device_sn")):
        print("✗ fault_index.json 为空或不存在，请先运行 phase1_preprocess_log.py")
        return

    jobs = segment_paths_from_index(fault_index, base_dir)
    if args.file:
        jobs = [j for j in jobs if args.file in str(j[0])]
    if args.max_segments is not None:
        jobs = jobs[: args.max_segments]

    if not jobs:
        print("没有可处理的故障窗口片段")
        return

    print(f"待处理片段数: {len(jobs)}")
    if args.dry_run:
        for seg_path, win, case_id, device_sn, source_stem in jobs[:20]:
            print(f"  {seg_path.name} | {source_stem} | {case_id} | {device_sn}")
        if len(jobs) > 20:
            print(f"  ... 共 {len(jobs)} 个")
        return

    import boto3
    from botocore.config import Config
    config = Config(read_timeout=300, connect_timeout=60, retries={"max_attempts": 3})
    bedrock_client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION, config=config)
    QA_PAIR_DIR.mkdir(parents=True, exist_ok=True)
    SEMANTIC_CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    # 按 source_stem 聚合
    by_stem: Dict[str, List[Dict[str, Any]]] = {}
    qa_by_stem: Dict[str, List[Dict[str, Any]]] = {}
    chunk_by_stem: Dict[str, List[Dict[str, Any]]] = {}

    for seg_path, win_meta, case_id, device_sn, source_stem in jobs:
        by_stem.setdefault(source_stem, []).append({
            "segment_path": seg_path,
            "win_meta": win_meta,
            "case_id": case_id,
            "device_sn": device_sn,
        })

    for source_stem, segment_infos in by_stem.items():
        qa_by_stem[source_stem] = []
        chunk_by_stem[source_stem] = []

        for seg_info in segment_infos:
            seg_path = seg_info["segment_path"]
            win_meta = seg_info["win_meta"]
            case_id = seg_info["case_id"]
            device_sn = seg_info["device_sn"]
            start_ts = win_meta.get("start_ts") or ""
            end_ts = win_meta.get("end_ts") or ""
            window_id = win_meta.get("window_id", 0)
            knowledge_layer = win_meta.get("knowledge_layer") or "evidence"

            log_text = load_segment_as_text(seg_path)
            if not log_text.strip():
                continue

            print(f"\n[{source_stem}] 片段 {seg_path.name} (window_{window_id})...")
            # QA
            qa_list = generate_qa_for_segment(
                bedrock_client, BEDROCK_MODEL_ID, log_text, case_id, device_sn, start_ts, end_ts
            )
            if qa_list:
                print(f"  ✓ 生成 {len(qa_list)} 条 QA")
                for q in qa_list:
                    normalized = normalize_qa_item(q)
                    if not normalized:
                        continue
                    normalized["source_segment"] = seg_path.name
                    qa_by_stem[source_stem].append(normalized)
            # Summary
            summary = generate_summary_for_segment(bedrock_client, BEDROCK_MODEL_ID, log_text)
            if summary:
                chunk_id = f"{source_stem}_log_window_{window_id}"
                chunk_by_stem[source_stem].append({
                    "metadata": {
                        "doc_name": source_stem,
                        "chunk_id": chunk_id,
                        "source_type": "log_fault_segment",
                        "knowledge_layer": knowledge_layer,
                        "case_id": case_id,
                        "device_sn": device_sn,
                        "segment_jsonl": _relpath(seg_path, base_dir),
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "window_id": window_id,
                    },
                    "content": summary,
                })
                print(f"  ✓ 已生成摘要")

            time.sleep(2.0)

        # 写出该 source_stem 的 qa_pair 与 semantic_chunk
        qa_list = qa_by_stem.get(source_stem) or []
        chunks = chunk_by_stem.get(source_stem) or []

        if qa_list:
            qa_path = QA_PAIR_DIR / f"{source_stem}_log_qa.json"
            qa_body = {
                "metadata": {
                    "source": source_stem,
                    "source_type": "log_fault_segment",
                    "total": len(qa_list),
                    "segment_count": len(segment_infos),
                    "knowledge_layer": (segment_infos[0].get("win_meta", {}) or {}).get("knowledge_layer", "evidence"),
                },
                "qa_pairs": qa_list,
            }
            qa_body["asset_meta"] = build_asset_record(
                asset_type="qa_dataset",
                knowledge_layer=qa_body["metadata"]["knowledge_layer"],
                display_name=source_stem,
                source_name=source_stem,
                source_path="",
                storage_path=qa_path,
                version=stable_version_from_mapping(qa_body),
                pipeline_stage="phase2",
                is_source_of_truth=False,
                stats={
                    "qa_count": len(qa_list),
                    "segment_count": len(segment_infos),
                },
                attributes={"source_type": "log_fault_segment"},
            ).to_dict()
            qa_path.write_text(json.dumps(qa_body, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  写入 QA: {qa_path.name} ({len(qa_list)} 条)")

        if chunks:
            chunk_path = SEMANTIC_CHUNK_DIR / f"{source_stem}_log_for_chunking.json"
            chunk_body = {
                "document_metadata": {
                    "doc_name": source_stem,
                    "source_type": "log_fault_segment",
                    "chunk_count": len(chunks),
                    "knowledge_layer": (segment_infos[0].get("win_meta", {}) or {}).get("knowledge_layer", "evidence"),
                },
                "references": [],
                "chunks": chunks,
            }
            chunk_body["asset_meta"] = build_asset_record(
                asset_type="semantic_dataset",
                knowledge_layer=chunk_body["document_metadata"]["knowledge_layer"],
                display_name=source_stem,
                source_name=source_stem,
                source_path="",
                storage_path=chunk_path,
                version=stable_version_from_mapping(chunk_body),
                pipeline_stage="phase2",
                is_source_of_truth=False,
                stats={
                    "chunk_count": len(chunks),
                },
                attributes={"source_type": "log_fault_segment"},
            ).to_dict()
            chunk_path.write_text(json.dumps(chunk_body, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  写入语义块: {chunk_path.name} ({len(chunks)} 条)")

    print("\nphase2_generate_log_chunk 完成。")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase2_log_chunk",
            script="phase2_generate_log_chunk.py",
            status="success",
            detail={"output_qa_pair": str(QA_PAIR_DIR), "output_semantic_chunk": str(SEMANTIC_CHUNK_DIR)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
