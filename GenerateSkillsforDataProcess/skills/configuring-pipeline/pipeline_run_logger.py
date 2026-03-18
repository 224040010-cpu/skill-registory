"""
pipeline_run_logger.py

流水线运行记录：以 JSONL（每行一个 JSON）追加写入，不重写整个文件。
用于记录「本次/历史」数据处理到哪一步、处理了哪些数据、成功或失败，便于断点续跑与排查。

本文件位于 skills/configuring-pipeline/，与 pipeline_config_loader / pipeline_config.json 同目录。

用法:
    from pipeline_run_logger import append_run_record, get_run_log_path

    append_run_record(
        step_id="phase0",
        script="phase0_sort_files.py",
        status="success",
        files_processed=8,
        detail={"by_category": {"memory_case": 3, "evidence": 5}},
    )
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _get_log_path() -> Path:
    try:
        from pipeline_config_loader import load_config
        cfg = load_config(ensure_dirs=False)
        out = cfg.get("output") or {}
        path = out.get("run_log")
        if path:
            return Path(path)
    except Exception:
        pass
    # 回退：项目根（本文件 parents[2]）/ data / processed_data / pipeline_run_log.jsonl
    _project_root = Path(__file__).resolve().parents[2]
    return _project_root / "data" / "processed_data" / "pipeline_run_log.jsonl"


def get_run_log_path() -> Path:
    """返回当前配置的 run_log 文件路径（供外部只读使用）。"""
    return _get_log_path()


def append_run_record(
    step_id: str,
    script: str,
    status: str,
    *,
    run_id: Optional[str] = None,
    files_processed: Optional[int] = None,
    detail: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    追加一条运行记录到 pipeline_run_log.jsonl（append，不重写）。

    参数:
        step_id: 步骤标识，如 phase0, phase1_excel, phase1_log, phase2_qa_md, phase3_text_qa, build_manifest
        script: 脚本文件名，如 phase0_sort_files.py
        status: success | failed | skipped
        run_id: 可选，同一轮流水线共用一个 run_id 便于分组；不传则自动生成
        files_processed: 可选，本步处理的文件/条数
        detail: 可选，结构化摘要，如 {"by_category": {...}, "output_paths": [...]}
        error: 可选，失败时的错误信息
    """
    log_path = _get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": run_id or str(uuid.uuid4()),
        "step_id": step_id,
        "script": script,
        "status": status,
    }
    if files_processed is not None:
        record["files_processed"] = files_processed
    if detail is not None:
        record["detail"] = detail
    if error is not None:
        record["error"] = error

    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def start_run() -> str:
    """
    开始一轮流水线时调用，返回本轮的 run_id。
    后续各 step 的 append_run_record 可传入此 run_id 以保持同组。
    """
    return str(uuid.uuid4())
