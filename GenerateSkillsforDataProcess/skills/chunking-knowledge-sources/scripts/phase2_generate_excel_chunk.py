"""
脚本：phase2_generate_excel_chunk.py

读取 data_prepare/table_cache 下的 CSV 表格，为每个 CSV 生成可检索的语义块 JSON，
输出到 data_prepare/semantic_chunk，供 phase3_text_QA_vectorize.py 统一向量化。

目标：
- 让 Agent 知道“有哪些表格、表格大致内容是什么、来源是什么”；
- 在需要时可通过 semantic_chunks 检索到对应表格摘要。

输出格式与 phase2_generate_for_chunking_json.py 保持一致：
- 每个 CSV 输出一份 *_for_chunking.json
- chunks 中每条含 metadata + content
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from common_schema import build_asset_record, stable_version_from_mapping

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
    TABLE_CACHE_DIR = Path(_cfg["intermediate"]["table_cache"])
    SEMANTIC_CHUNK_DIR = Path(_cfg["intermediate"]["semantic_chunk"])
    MARKDOWN_DIR = Path(_cfg["intermediate"]["markdown"])
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    TABLE_CACHE_DIR = PROCESSED_DATA_DIR / "table_cache"
    SEMANTIC_CHUNK_DIR = PROCESSED_DATA_DIR / "semantic_chunk"
    MARKDOWN_DIR = PROCESSED_DATA_DIR / "markdown"

EXCEL_SOURCE_MAP_PATH = TABLE_CACHE_DIR / "_excel_source_map.jsonl"

TABLE_PLACEHOLDER_RE = re.compile(
    r'\[\[TABLE\s+type="file"\s+summary="([^"]*)"\s+path="([^"]+)"\s*\]\]'
)


def _relpath(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_sidecar(path: Path) -> Dict[str, Any]:
    sidecar = path.with_name(path.name + ".asset_meta.json")
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_excel_source_map() -> Dict[str, Dict[str, Any]]:
    """
    加载 Excel -> CSV 的轻量来源映射。
    若同一 csv_name 有多条记录，保留最后一条，适配追加式 jsonl。
    """
    mapping: Dict[str, Dict[str, Any]] = {}
    if not EXCEL_SOURCE_MAP_PATH.exists():
        return mapping
    with EXCEL_SOURCE_MAP_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            csv_name = str(rec.get("csv_name") or "").strip()
            if not csv_name:
                continue
            mapping[csv_name] = rec
    return mapping


def _read_processed_asset_meta_from_markdown_path(markdown_path: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    如果该表格来自 PDF/MD 抽取，则 markdown_path 能帮助反查对应 processed.json，
    从而继承文档的 knowledge_layer / source_path / source_raw。
    """
    if not markdown_path:
        return {}, {}
    md_path = DATA_PREPARE_DIR / markdown_path.replace("\\", "/")
    if not md_path.exists():
        return {}, {}
    processed_name = md_path.stem + "_processed.json"
    processed_path = MARKDOWN_DIR / processed_name
    if not processed_path.exists():
        return {}, {}
    try:
        data = json.loads(processed_path.read_text(encoding="utf-8"))
        return data.get("metadata") or {}, data.get("asset_meta") or {}
    except Exception:
        return {}, {}


def load_table_summary_index(markdown_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    从 markdown/*.md 中提取 TABLE 占位符里的摘要与来源信息。
    返回键为 csv 文件名，值包含 summary/markdown_path/table_path。
    """
    index: Dict[str, Dict[str, str]] = {}
    if not markdown_dir.exists():
        return index

    for md_path in sorted(markdown_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for m in TABLE_PLACEHOLDER_RE.finditer(text):
            summary = (m.group(1) or "").strip()
            raw_path = (m.group(2) or "").strip().replace("\\", "/")
            if not raw_path:
                continue
            csv_name = Path(raw_path).name
            if not csv_name:
                continue
            index[csv_name] = {
                "summary": summary,
                "markdown_path": _relpath(md_path, DATA_PREPARE_DIR),
                "table_path": raw_path,
            }
    return index


def read_csv_rows(csv_path: Path) -> Tuple[List[List[str]], str]:
    """
    读取 CSV，优先 utf-8-sig，失败后回退 gb18030。
    返回 (rows, encoding)。
    """
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = csv_path.read_text(encoding=enc)
            rows = list(csv.reader(text.splitlines()))
            return rows, enc
        except Exception:
            continue
    # 最后兜底：忽略非法字符
    text = csv_path.read_text(encoding="utf-8", errors="ignore")
    rows = list(csv.reader(text.splitlines()))
    return rows, "utf-8(ignore)"


def infer_doc_name(csv_name: str) -> str:
    m = re.match(r"^(.*)_table_(\d+)\.csv$", csv_name)
    if m:
        return m.group(1)
    return Path(csv_name).stem


def infer_table_index(csv_name: str) -> Optional[int]:
    m = re.match(r"^.*_table_(\d+)\.csv$", csv_name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _truncate(s: str, max_chars: int = 160) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= max_chars else s[: max_chars - 1] + "…"


def build_fallback_summary(
    csv_name: str,
    headers: List[str],
    data_rows: List[List[str]],
    row_count: int,
    col_count: int,
) -> str:
    """无现成摘要时，基于结构生成可检索的简要摘要。"""
    non_empty_headers = [h for h in headers if h]
    key_cols = "、".join(non_empty_headers[:8]) if non_empty_headers else "无明确表头"

    samples: List[str] = []
    for row in data_rows[:3]:
        cells = [_truncate(c) for c in row[:4] if str(c).strip()]
        if cells:
            samples.append(" / ".join(cells))

    sample_text = "；".join(samples) if samples else "无示例值"
    return (
        f"表格 {csv_name} 包含 {row_count} 行、{col_count} 列的结构化数据，"
        f"主要字段包括：{key_cols}。示例值：{sample_text}。"
    )


def build_chunk_content(
    csv_name: str,
    doc_name: str,
    summary: str,
    headers: List[str],
    data_rows: List[List[str]],
    row_count: int,
    col_count: int,
) -> str:
    header_line = " | ".join([_truncate(h, 80) for h in headers if h]) if headers else "(无表头)"
    sample_lines: List[str] = []
    for i, row in enumerate(data_rows[:5], start=1):
        shown = " | ".join([_truncate(c, 80) for c in row[:8]])
        sample_lines.append(f"- 第{i}行: {shown}")
    if not sample_lines:
        sample_lines.append("- (无数据行)")

    return "\n".join(
        [
            f"# 表格摘要：{csv_name}",
            "",
            f"文档来源：{doc_name}",
            f"行列规模：{row_count} 行 × {col_count} 列",
            f"摘要：{summary}",
            "",
            "表头：",
            header_line,
            "",
            "示例数据：",
            *sample_lines,
        ]
    ).strip()


def generate_one_csv_for_chunking(
    csv_path: Path,
    summary_index: Dict[str, Dict[str, str]],
    excel_source_map: Dict[str, Dict[str, Any]],
    out_dir: Path,
) -> Path:
    csv_name = csv_path.name
    rows, encoding = read_csv_rows(csv_path)

    if not rows:
        headers: List[str] = []
        data_rows: List[List[str]] = []
    else:
        headers = [str(x).strip() for x in rows[0]]
        data_rows = [[str(x).strip() for x in r] for r in rows[1:]]

    row_count = len(data_rows)
    col_count = max((len(r) for r in rows), default=0)
    doc_name = infer_doc_name(csv_name)
    table_index = infer_table_index(csv_name)
    rel_csv_path = _relpath(csv_path, DATA_PREPARE_DIR)
    sidecar = _read_sidecar(csv_path)
    excel_origin = excel_source_map.get(csv_name, {})

    summary_info = summary_index.get(csv_name, {})
    summary = (summary_info.get("summary") or "").strip()
    summary_source = "markdown_placeholder" if summary else "auto_fallback"
    markdown_path = summary_info.get("markdown_path", "")
    processed_meta, processed_asset_meta = _read_processed_asset_meta_from_markdown_path(markdown_path)
    knowledge_layer = (
        processed_asset_meta.get("knowledge_layer")
        or sidecar.get("knowledge_layer")
        or excel_origin.get("knowledge_layer")
        or "evidence"
    )
    inherited_source_path = (
        processed_meta.get("source_path")
        or sidecar.get("source_path")
        or excel_origin.get("origin_excel_path")
        or rel_csv_path
    )
    inherited_source_name = (
        processed_meta.get("source_raw")
        or sidecar.get("source_name")
        or excel_origin.get("source_name")
        or doc_name
    )
    inherited_created_at = (
        processed_asset_meta.get("created_at")
        or sidecar.get("created_at")
        or excel_origin.get("emitted_at")
    )
    inherited_updated_at = (
        processed_asset_meta.get("updated_at")
        or sidecar.get("updated_at")
        or excel_origin.get("emitted_at")
    )
    if not summary:
        summary = build_fallback_summary(csv_name, headers, data_rows, row_count, col_count)

    content = build_chunk_content(
        csv_name=csv_name,
        doc_name=doc_name,
        summary=summary,
        headers=headers,
        data_rows=data_rows,
        row_count=row_count,
        col_count=col_count,
    )

    chunk_id = f"{Path(csv_name).stem}__table_chunk_0"
    out_body: Dict[str, Any] = {
        "document_metadata": {
            "doc_name": doc_name,
            "source_type": "table_csv",
            "source_path": rel_csv_path,
            "table_index": table_index,
            "csv_name": csv_name,
            "encoding": encoding,
            "row_count": row_count,
            "column_count": col_count,
            "chunk_count": 1,
            "summary_source": summary_source,
            "knowledge_layer": knowledge_layer,
        },
        "references": [],
        "chunks": [
            {
                "metadata": {
                    "doc_name": doc_name,
                    "chunk_id": chunk_id,
                    "section_title": f"table:{csv_name}",
                    "section_index": 0,
                    "char_count": len(content),
                    "refs_in_chunk": [],
                    "source_path": rel_csv_path,
                    "markdown_path": summary_info.get("markdown_path", ""),
                    "source_type": "table_csv",
                    "knowledge_layer": knowledge_layer,
                    "csv_name": csv_name,
                    "table_index": table_index if table_index is not None else -1,
                    "row_count": row_count,
                    "column_count": col_count,
                    "summary_source": summary_source,
                    "table_summary": summary[:1500],
                },
                "content": content,
            }
        ],
    }
    out_body["asset_meta"] = build_asset_record(
        asset_type="semantic_dataset",
        knowledge_layer=knowledge_layer,
        display_name=doc_name,
        source_name=inherited_source_name,
        source_path=inherited_source_path,
        storage_path=out_dir / f"{Path(csv_name).stem}_for_chunking.json",
        version=stable_version_from_mapping(out_body),
        created_at=inherited_created_at,
        updated_at=inherited_updated_at,
        pipeline_stage="phase2",
        is_source_of_truth=False,
        stats={
            "chunk_count": 1,
            "row_count": row_count,
            "column_count": col_count,
        },
        attributes={
            "source_type": "table_csv",
            "csv_name": csv_name,
            "table_index": table_index,
            "markdown_path": markdown_path,
            "origin_excel_path": excel_origin.get("origin_excel_path", ""),
            "sheet_name": excel_origin.get("sheet_name", ""),
        },
    ).to_dict()

    out_name = f"{Path(csv_name).stem}_for_chunking.json"
    out_path = out_dir / out_name
    out_path.write_text(json.dumps(out_body, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="读取 table_cache/*.csv，生成 semantic_chunk/*_for_chunking.json（每个 CSV 一份）"
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="仅处理指定 CSV（支持写文件名片段）",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的 *_for_chunking.json（默认已存在则跳过）",
    )
    args = parser.parse_args()

    if not TABLE_CACHE_DIR.exists():
        print(f"✗ 目录不存在: {TABLE_CACHE_DIR}")
        return

    csv_files = sorted(TABLE_CACHE_DIR.glob("*.csv"))
    if args.file:
        key = args.file.strip()
        csv_files = [p for p in csv_files if key in p.name]
    if not csv_files:
        print("没有可处理的 CSV 文件")
        return

    summary_index = load_table_summary_index(MARKDOWN_DIR)
    excel_source_map = _load_excel_source_map()
    SEMANTIC_CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    print(f"待处理 CSV: {len(csv_files)}")
    print(f"输出目录: {SEMANTIC_CHUNK_DIR}")

    done = 0
    skipped = 0
    for csv_path in csv_files:
        out_name = f"{csv_path.stem}_for_chunking.json"
        out_path = SEMANTIC_CHUNK_DIR / out_name
        if out_path.exists() and not args.overwrite:
            print(f"  - 跳过(已存在): {out_name}")
            skipped += 1
            continue
        try:
            written = generate_one_csv_for_chunking(csv_path, summary_index, excel_source_map, SEMANTIC_CHUNK_DIR)
            print(f"  [OK] 生成: {written.name}")
            done += 1
        except Exception as e:
            print(f"  [ERR] 失败: {csv_path.name} ({type(e).__name__}: {e})")

    print(f"\n完成。生成 {done} 个，跳过 {skipped} 个。")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase2_excel_chunk",
            script="phase2_generate_excel_chunk.py",
            status="success",
            files_processed=done + skipped,
            detail={"generated": done, "skipped": skipped},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
