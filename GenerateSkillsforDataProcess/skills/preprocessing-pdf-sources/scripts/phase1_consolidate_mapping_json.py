"""
脚本：phase1_consolidate_mapping_json.py

将 phase1 预处理阶段追加写入的「文档引用边」整合成标准字典 JSON，便于下游消费与人工维护。

处理逻辑：
- 输入（默认）：data_prepare/markdown/mapping.json。
  - 支持 JSON Lines：每行一个对象 {"docA":"docB"}，多行会合并为边集合。
  - 兼容旧格式：单行标准 JSON 为 {"docA":["docB","docC"]} 或 [{"docA":"docB"}, ...]，同样解析为 (源, 目标) 边。
- 去重与聚合：将所有边收集为 (source, target) 集合后，按 source 聚合 target 列表，去重；
  若配置 SORT_TARGETS 则对每个 source 的 target 列表排序，便于 diff 与阅读。
- 输出（默认）：data_prepare/markdown/mapping_merged.json，为标准字典 {"docA":["docB","docC"], ...}。
- 可随时在 phase1 跑完或手工编辑 mapping.json 后执行本脚本，独立于其他 pipeline 步骤。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple


# ============================================================================
# 【配置区域】
# ============================================================================
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
    MARKDOWN_DIR = Path(_cfg["intermediate"]["markdown"])
except Exception:
    _cfg = {}
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    MARKDOWN_DIR = PROCESSED_DATA_DIR / "markdown"

MAPPING_JSON_PATH = MARKDOWN_DIR / "mapping.json"
OUTPUT_JSON_PATH = MARKDOWN_DIR / "mapping_merged.json"
SORT_TARGETS = bool((_cfg.get("pdf") or {}).get("sort_targets", True))
# ============================================================================
# 【配置区域结束】
# ============================================================================


def load_mapping_edges_any_format(mapping_path: Path) -> Set[Tuple[str, str]]:
    p = Path(mapping_path)
    if not p.exists():
        return set()
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return set()

    edges: Set[Tuple[str, str]] = set()

    # 先尝试当成标准 JSON 解析
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for src, v in obj.items():
                src2 = str(src).strip()
                if not src2:
                    continue
                if isinstance(v, list):
                    for t in v:
                        t2 = str(t).strip()
                        if t2:
                            edges.add((src2, t2))
                else:
                    t2 = str(v).strip()
                    if t2:
                        edges.add((src2, t2))
            return edges
        if isinstance(obj, list):
            for it in obj:
                if isinstance(it, dict) and len(it) == 1:
                    (src, tgt), *_ = it.items()
                    src2 = str(src).strip()
                    tgt2 = str(tgt).strip()
                    if src2 and tgt2:
                        edges.add((src2, tgt2))
            return edges
    except Exception:
        pass

    # JSON Lines：逐行解析
    for ln in text.splitlines():
        ln2 = ln.strip()
        if not ln2:
            continue
        try:
            obj = json.loads(ln2)
            if isinstance(obj, dict) and len(obj) == 1:
                (src, tgt), *_ = obj.items()
                src2 = str(src).strip()
                tgt2 = str(tgt).strip()
                if src2 and tgt2:
                    edges.add((src2, tgt2))
        except Exception:
            continue

    return edges


def consolidate_mapping(edges: Set[Tuple[str, str]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for src, tgt in sorted(edges):
        out.setdefault(src, [])
        if tgt not in out[src]:
            out[src].append(tgt)
    if SORT_TARGETS:
        for k in list(out.keys()):
            out[k] = sorted(out[k])
    return out


def main() -> None:
    edges = load_mapping_edges_any_format(MAPPING_JSON_PATH)
    merged = consolidate_mapping(edges)
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"输入：{MAPPING_JSON_PATH}")
    print(f"输出：{OUTPUT_JSON_PATH}")
    print(f"文档数：{len(merged)}，边数：{len(edges)}")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase1_consolidate_mapping",
            script="phase1_consolidate_mapping_json.py",
            status="success",
            detail={"doc_count": len(merged), "edge_count": len(edges)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()

