"""
脚本：phase1_preprocess_log.py

工业级日志预处理（与 phase1 PDF/Excel 并列的日志支线）。仅处理并记录「有故障锚点」的日志；
无锚点的文件仍会写出 structured jsonl，但不写入 fault_windows、不进入 log_index 与 fault_index。

处理流程（按方案 docs_phase1_log_fault_segments_design.md）：

1. 采集与结构化 (Parsing & Structuring)
   - 输入：data_prepare/source_file 下所有 .log（及可选 .txt）。
   - 使用正则解析 DTM/CCU 格式，提取每行 timestamp、module、level、tid、message；多行续行与前一条合并，
     无法识别的行按纯文本保留。
   - 合并「除时间外完全相同」的记录：按 (module, level, tid, message) 分组，每组保留一条，ts/ts_epoch 取该组最晚
     （见 docs_merge_identical_log_records.md），再按 ts_epoch 升序排序。
   - 输出：log_cache/structured/<safe_stem>.jsonl（每个源 log 一份，无论是否有锚点）。

2. 故障检测与故障窗口 (Fault Detection & Fault Windows)（仅当存在锚点时执行）
   - 在合并后的 structured 记录上，按配置的纳入词/正则与排除项判断 message 是否为故障锚点（ts_epoch 非空；
     先匹配排除项，再匹配纳入项；见 FAULT_PHRASES_INCLUDE / FAULT_PHRASES_EXCLUDE）。
   - 每个锚点生成时间区间 [t - window_seconds_before, t + window_seconds_after]；使用间隔阈值 merge_gap_seconds
     合并区间（两段间隔超过该秒数则不合并，另起新段），得到故障窗口列表。
   - 仅当存在锚点且合并后至少一段时：写出 log_cache/fault_windows/<safe_stem>_fault_windows.json（索引）
     以及 <safe_stem>_window_<id>.jsonl（各窗口内的日志行）。无锚点时**不写** fault_windows 相关文件。

3. 索引（仅包含有故障锚点的文件）
   - log_index.json：case_key -> 该案例下「有锚点」的源 .log 相对路径列表。
   - fault_index.json：by_case_id / by_device_sn -> 各条目的 structured 路径、fault_windows_file、segments 列表，
     供 Agent 根据 case_id/device_sn 查故障片段。无锚点的文件不会出现在上述两个索引中。

命令行：--file 指定单文件；--before/--after 故障窗口前后秒数；--gap 合并间隔阈值（秒）。
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from common_schema import (
    build_asset_record,
    infer_layer_from_source_tree,
    sha1_file,
    stable_version_from_mapping,
)

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
    SOURCE_DIR = Path(_cfg["intermediate"]["source_file"])
    LOG_CACHE_DIR = Path(_cfg["intermediate"]["log_cache"])
except Exception:
    _cfg = {}
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    SOURCE_DIR = DATA_PREPARE_DIR / "source_file"
    LOG_CACHE_DIR = PROCESSED_DATA_DIR / "log_cache"

STRUCTURED_DIR = LOG_CACHE_DIR / "structured"
FAULT_WINDOWS_DIR = LOG_CACHE_DIR / "fault_windows"
LOG_INDEX_FILENAME = "log_index.json"
FAULT_INDEX_FILENAME = "fault_index.json"

# 从 pipeline_config.json 的 log 节读取
_log = _cfg.get("log") or {}
LOG_SUFFIXES = set(_log.get("log_suffixes", [".log"]))
TEXT_SUFFIXES = set(_log.get("text_suffixes", []))
FAULT_WINDOW_SECONDS_BEFORE = int(_log.get("fault_window_seconds_before", 120))
FAULT_WINDOW_SECONDS_AFTER = int(_log.get("fault_window_seconds_after", 300))
FAULT_MERGE_GAP_SECONDS = int(_log.get("fault_merge_gap_seconds", 120))
FAULT_PHRASES_INCLUDE = list(_log.get("fault_phrases_include", [
    "fail", "failed", "failure", "error", "err", "timeout", "time out",
    "reconnect", "exception", "abort", "fault", "reset",
    "错误", "失败", "异常", "故障", "超时",
    "rcvlen : 0", "rcvlen: 0", "rcvlen :0", "rcvLen : 0", "rcvLen: 0",
]))
FAULT_PHRASES_EXCLUDE = list(_log.get("fault_phrases_exclude", [
    "open fail = 0", "open fail=0", "create success",
    "communication setup performance time", "getallserialcomfailednum null",
    "getprop persist.maxicharger.usbhuberrornum", "event_timeout_sounds", "timeoutmsounds",
    "erase timeout element", "totalerr=0", "workstatus=0", "reconnectupdata:0",
    "curstatus=0", "m_ccurtsta= 0",
]))
FAULT_REGEX_INCLUDE = [
    re.compile(r"receive.*fail", re.I),
]

# DTM 行正则（示例：3#:10:[2024-10-23 10:00:27.306]:wallboxTCU_AcuDCM230:debug:417:tid:2873:message）
DTM_LINE_RE = re.compile(
    r"^[0-9]#:[0-9]+:\[([^\]]+)\]:([^:]+):([^:]+):(\d+):tid:(\d+):(.*)$",
    re.DOTALL,
)
# 时间戳解析（用于时间窗）
DATETIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?")
# ============================================================================


@dataclass
class LogRecord:
    """单条结构化日志。"""
    ts: Optional[str]  # ISO 或原样字符串
    ts_epoch: Optional[float]  # 用于时间窗分块
    module: str
    level: str
    tid: str
    message: str
    raw_line: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "ts_epoch": self.ts_epoch,
            "module": self.module,
            "level": self.level,
            "tid": self.tid,
            "message": self.message,
        }


def _parse_ts_to_epoch(ts_str: str) -> Optional[float]:
    """将 [2024-10-23 10:00:27.306] 风格字符串转为 epoch 秒。"""
    m = DATETIME_RE.match(ts_str.strip())
    if not m:
        return None
    y, mo, d, h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
    ms = int(m.group(7)) if m.lastindex >= 7 and m.group(7) else 0
    try:
        dt = datetime(y, mo, d, h, mi, s, ms * 1000)
        return dt.timestamp()
    except Exception:
        return None


def _message_to_template(message: str) -> str:
    """将 message 转为模板：数字、引号内字符串替换为 <*>，合并空白。"""
    if not message:
        return ""
    s = message
    s = re.sub(r"\d+", "<*>", s)
    s = re.sub(r'"[^"]*"', "<*>", s)
    s = re.sub(r"'[^']*'", "<*>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:500]  # 避免过长


def _merge_identical_records_keep_latest(records: List[LogRecord]) -> List[LogRecord]:
    """
    合并「除时间外完全相同」的日志：按 (module, level, tid, message) 分组，
    每组保留一条，ts/ts_epoch 取该组内最晚时间，再按 ts_epoch 升序排序。
    见 docs_merge_identical_log_records.md
    """
    if not records:
        return []
    groups: Dict[Tuple[str, str, str, str], List[LogRecord]] = defaultdict(list)
    for r in records:
        key = (r.module or "", r.level or "", r.tid or "", r.message or "")
        groups[key].append(r)

    merged: List[LogRecord] = []
    for group in groups.values():
        # 取 ts_epoch 最大的那条；若全为 None 则取第一条
        best = max(
            group,
            key=lambda x: (x.ts_epoch if x.ts_epoch is not None else -1.0),
        )
        merged.append(best)
    # 按 ts_epoch 升序；无时间戳的放最前
    merged.sort(key=lambda x: (x.ts_epoch if x.ts_epoch is not None else -1.0))
    return merged


def _parse_log_lines(lines: List[str]) -> List[LogRecord]:
    """解析行列表，产出 LogRecord 列表；续行合并到上一条。"""
    records: List[LogRecord] = []
    for line in lines:
        line_stripped = line.strip()
        m = DTM_LINE_RE.match(line)
        if m:
            ts_str, module, level, _, tid, msg = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
            ts_epoch = _parse_ts_to_epoch(ts_str)
            records.append(
                LogRecord(
                    ts=ts_str,
                    ts_epoch=ts_epoch,
                    module=module.strip(),
                    level=(level or "").strip().lower(),
                    tid=tid.strip(),
                    message=(msg or "").strip(),
                    raw_line=line[:1000],
                )
            )
        else:
            if records and (line.startswith(" ") or line.startswith("\t") or not line_stripped):
                records[-1].message = (records[-1].message + "\n" + line).strip()
                records[-1].raw_line = (records[-1].raw_line + "\n" + line)[:1000]
            elif line_stripped:
                records.append(
                    LogRecord(
                        ts=None,
                        ts_epoch=None,
                        module="",
                        level="",
                        tid="",
                        message=line_stripped,
                        raw_line=line[:1000],
                    )
                )
    return records


def _extract_case_id_and_sn(filename_stem: str) -> Tuple[str, str]:
    """从日志文件名 stem 提取 case_id（EVSHWT-xxxx）和 device_sn（若存在）。"""
    case_id = ""
    device_sn = ""
    # EVSHWT-1234 或 EVSHWT-1234-xxx
    ev_match = re.search(r"EVSHWT-\d+", filename_stem, re.I)
    if ev_match:
        case_id = ev_match.group(0)
    # 设备 SN 常见格式：DE0060B1GNAC00001G、AE0022A1GP6C00189R
    sn_match = re.search(r"[A-Z]{2}\d{4}[A-Z0-9]{10,}", filename_stem)
    if sn_match:
        device_sn = sn_match.group(0)
    return case_id, device_sn


def _sanitize_stem_for_path(stem: str) -> str:
    """生成可做文件名/id 的 stem（去掉非法字符，截断过长）。"""
    s = re.sub(r'[<>:"/\\|?*;]', "_", stem)
    s = s.strip("._ ")[:120]
    return s or "unknown"


def _is_fault_record(record: LogRecord) -> bool:
    """
    规则判定是否为故障锚点：ts_epoch 非空；先排除项再纳入项。
    任何与错误有关的字眼均纳入，仅命中排除项时不计为锚点。
    """
    if record.ts_epoch is None:
        return False
    msg = (record.message or "").strip()
    if not msg:
        return False
    msg_lower = msg.lower()
    for phrase in FAULT_PHRASES_EXCLUDE:
        if phrase.lower() in msg_lower:
            return False
    for phrase in FAULT_PHRASES_INCLUDE:
        if phrase.lower() in msg_lower:
            return True
    for rx in FAULT_REGEX_INCLUDE:
        if rx.search(msg):
            return True
    return False


def _get_fault_anchors(records: List[LogRecord]) -> List[Tuple[float, str]]:
    """返回 [(ts_epoch, message), ...] 锚点列表（按时间升序）。"""
    anchors: List[Tuple[float, str]] = []
    for r in records:
        if _is_fault_record(r) and r.ts_epoch is not None:
            anchors.append((r.ts_epoch, (r.message or "")[:200]))
    anchors.sort(key=lambda x: x[0])
    return anchors


def _merge_intervals(
    intervals: List[Tuple[float, float]],
    gap_threshold_sec: Optional[int] = None,
) -> List[Tuple[float, float]]:
    """
    合并时间区间；若两段间隔超过 gap_threshold_sec 秒则不合并，另起新段。
    gap_threshold_sec=None 时视为 0（仅重叠或相邻才合并）。
    """
    if not intervals:
        return []
    if gap_threshold_sec is None:
        gap_threshold_sec = 0
    sorted_i = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: List[Tuple[float, float]] = [sorted_i[0]]
    for a, b in sorted_i[1:]:
        la, lb = merged[-1]
        if a <= lb + gap_threshold_sec:
            merged[-1] = (la, max(lb, b))
        else:
            merged.append((a, b))
    return merged


def _epoch_to_ts(epoch: float) -> str:
    """将 epoch 秒转为可读时间字符串。"""
    try:
        dt = datetime.fromtimestamp(epoch)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + f".{int((epoch % 1) * 1000):03d}"
    except Exception:
        return str(epoch)


class LogPreprocessor:
    def __init__(
        self,
        source_dir: Path = SOURCE_DIR,
        log_cache_dir: Path = LOG_CACHE_DIR,
        structured_dir: Optional[Path] = None,
        fault_windows_dir: Optional[Path] = None,
        window_seconds_before: int = FAULT_WINDOW_SECONDS_BEFORE,
        window_seconds_after: int = FAULT_WINDOW_SECONDS_AFTER,
        merge_gap_seconds: Optional[int] = None,
    ):
        self.source_dir = Path(source_dir)
        self.log_cache_dir = Path(log_cache_dir)
        self.structured_dir = Path(structured_dir or log_cache_dir / "structured")
        self.fault_windows_dir = Path(fault_windows_dir or log_cache_dir / "fault_windows")
        self.window_seconds_before = window_seconds_before
        self.window_seconds_after = window_seconds_after
        self.merge_gap_seconds = merge_gap_seconds if merge_gap_seconds is not None else FAULT_MERGE_GAP_SECONDS
        self.structured_dir.mkdir(parents=True, exist_ok=True)
        self.fault_windows_dir.mkdir(parents=True, exist_ok=True)

    def _collect_log_files(self) -> List[Path]:
        suffixes = LOG_SUFFIXES | TEXT_SUFFIXES
        files: List[Path] = []
        for s in sorted(suffixes):
            files.extend(self.source_dir.rglob(f"*{s}"))
        return sorted(set(files))

    def _write_asset_meta_sidecar(
        self,
        *,
        output_path: Path,
        source_path: Path,
        asset_type: str,
        display_name: str,
        stats: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        对 structured jsonl 这类非 JSON 顶层对象，写 sidecar 保存统一资产字段。
        """
        knowledge_layer = infer_layer_from_source_tree(source_path, self.source_dir)
        asset_record = build_asset_record(
            asset_type=asset_type,
            knowledge_layer=knowledge_layer,
            display_name=display_name,
            source_name=source_path.name,
            source_path=source_path,
            storage_path=output_path,
            version=sha1_file(output_path),
            pipeline_stage="phase1",
            is_source_of_truth=True,
            stats=stats or {},
            attributes=attributes or {},
        )
        sidecar_path = output_path.with_name(output_path.name + ".asset_meta.json")
        sidecar_path.write_text(
            json.dumps(asset_record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _case_key_from_stem(self, stem: str) -> str:
        """用于 log_index 的 key：取 stem 中第一个 __ 之前的部分（案例目录名）。"""
        if "__" in stem:
            return stem.split("__", 1)[0].strip()
        return stem.strip()

    def process_one_log_file(self, log_path: Path) -> Dict[str, Any]:
        """
        处理单个日志文件：解析 -> 结构化 JSONL -> 故障检测与故障窗口 -> 写 fault_windows 索引与片段。
        返回本文件的统计信息（含 fault_index 所需字段）。
        """
        rel_path = log_path.relative_to(self.source_dir) if log_path.is_relative_to(self.source_dir) else log_path.name
        stem = log_path.stem
        case_key = self._case_key_from_stem(stem)
        case_id, device_sn = _extract_case_id_and_sn(stem)
        safe_stem = _sanitize_stem_for_path(stem)
        knowledge_layer = infer_layer_from_source_tree(log_path, self.source_dir)

        try:
            raw = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"path": str(log_path), "error": str(e), "records": 0, "case_key": case_key}

        lines = raw.splitlines()
        records = _parse_log_lines(lines)
        if not records:
            return {"path": str(rel_path), "records": 0, "case_key": case_key, "case_id": case_id, "device_sn": device_sn}

        # 合并除时间外完全相同的记录，时间取最晚（见 docs_merge_identical_log_records.md）
        records = _merge_identical_records_keep_latest(records)

        # 1) 写结构化 JSONL
        jsonl_path = self.structured_dir / f"{safe_stem}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        self._write_asset_meta_sidecar(
            output_path=jsonl_path,
            source_path=log_path,
            asset_type="log_structured",
            display_name=safe_stem,
            stats={"record_count": len(records)},
            attributes={"case_id": case_id, "case_key": case_key, "device_sn": device_sn},
        )

        # 2) 故障检测 -> 锚点 -> 时间窗合并 -> 写 fault_windows 索引与片段
        anchors = _get_fault_anchors(records)

        def _rel(path: Path) -> str:
            try:
                return path.relative_to(DATA_PREPARE_DIR).as_posix()
            except ValueError:
                return str(path)

        rel_structured = _rel(jsonl_path)
        fault_index_entry: Dict[str, Any] = {
            "structured": rel_structured,
            "fault_windows_file": "",
            "segments": [],
            "device_sn": device_sn,
            "case_key": case_key,
            "knowledge_layer": knowledge_layer,
        }
        fault_windows_meta: List[Dict[str, Any]] = []

        if not anchors:
            # 无锚点：不写 fault_windows、不进入映射，仅返回基础信息（便于统计）
            return {
                "path": str(rel_path),
                "records": len(records),
                "case_key": case_key,
                "case_id": case_id,
                "device_sn": device_sn,
                "jsonl": str(jsonl_path),
                "knowledge_layer": knowledge_layer,
                "segments": [],
            }

        intervals: List[Tuple[float, float]] = []
        for epoch, _ in anchors:
            start = epoch - self.window_seconds_before
            end = epoch + self.window_seconds_after
            intervals.append((start, end))
        merged = _merge_intervals(intervals, gap_threshold_sec=self.merge_gap_seconds)

        for win_id, (start_epoch, end_epoch) in enumerate(merged):
            window_records = [r for r in records if r.ts_epoch is not None and start_epoch <= r.ts_epoch <= end_epoch]
            anchor_in_window = [msg for e, msg in anchors if start_epoch <= e <= end_epoch]
            segment_name = f"{safe_stem}_window_{win_id}.jsonl"
            segment_path = self.fault_windows_dir / segment_name
            with segment_path.open("w", encoding="utf-8") as f:
                for r in window_records:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            rel_segment = _rel(segment_path)
            fault_index_entry["segments"].append(rel_segment)
            fault_windows_meta.append({
                "window_id": win_id,
                "start_ts": _epoch_to_ts(start_epoch),
                "end_ts": _epoch_to_ts(end_epoch),
                "start_epoch": start_epoch,
                "end_epoch": end_epoch,
                "fault_anchor_count": len(anchor_in_window),
                "record_count": len(window_records),
                "segment_jsonl": rel_segment,
                "sample_fault_messages": list(dict.fromkeys(anchor_in_window))[:5],
            })

        fault_windows_index_path = self.fault_windows_dir / f"{safe_stem}_fault_windows.json"
        fault_index_entry["fault_windows_file"] = _rel(fault_windows_index_path)
        index_body = {
            "source_jsonl": rel_structured,
            "source_stem": safe_stem,
            "case_id": case_id,
            "case_key": case_key,
            "device_sn": device_sn,
            "knowledge_layer": knowledge_layer,
            "total_records": len(records),
            "window_seconds_before": self.window_seconds_before,
            "window_seconds_after": self.window_seconds_after,
            "merge_gap_seconds": self.merge_gap_seconds,
            "fault_windows": fault_windows_meta,
        }
        index_body["asset_meta"] = build_asset_record(
            asset_type="log_fault_window_index",
            knowledge_layer=knowledge_layer,
            display_name=safe_stem,
            source_name=log_path.name,
            source_path=log_path,
            storage_path=fault_windows_index_path,
            version=stable_version_from_mapping(index_body),
            pipeline_stage="phase1",
            is_source_of_truth=True,
            stats={
                "window_count": len(fault_windows_meta),
                "total_records": len(records),
            },
            attributes={
                "case_id": case_id,
                "case_key": case_key,
                "device_sn": device_sn,
                "window_seconds_before": self.window_seconds_before,
                "window_seconds_after": self.window_seconds_after,
                "merge_gap_seconds": self.merge_gap_seconds,
            },
        ).to_dict()
        fault_windows_index_path.write_text(json.dumps(index_body, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "path": str(rel_path),
            "records": len(records),
            "case_key": case_key,
            "case_id": case_id,
            "device_sn": device_sn,
            "jsonl": str(jsonl_path),
            "knowledge_layer": knowledge_layer,
            "fault_windows_file": fault_index_entry["fault_windows_file"],
            "segments": fault_index_entry["segments"],
            "fault_index_entry": fault_index_entry,
        }

    def build_log_index(self, file_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """根据处理结果构建 case_key -> [相对路径列表] 的索引。仅包含有故障锚点的文件。"""
        index: Dict[str, List[str]] = defaultdict(list)
        for r in file_results:
            path = r.get("path") or r.get("source_path")
            if not path or r.get("error"):
                continue
            if not r.get("segments"):
                continue  # 无锚点的不进入映射
            case_key = r.get("case_key") or "unknown"
            index[case_key].append(path)
        return dict(index)

    def build_fault_index(self, file_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建 fault_index.json：by_case_id、by_device_sn -> structured + fault_windows 文件 + segments。"""
        by_case_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        by_device_sn: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in file_results:
            if r.get("error") or "fault_index_entry" not in r:
                continue
            entry = r["fault_index_entry"]
            case_id = (r.get("case_id") or "").strip()
            device_sn = (r.get("device_sn") or "").strip()
            if case_id:
                by_case_id[case_id].append(entry)
            if device_sn:
                by_device_sn[device_sn].append(entry)
        return {"by_case_id": dict(by_case_id), "by_device_sn": dict(by_device_sn)}


def main():
    parser = argparse.ArgumentParser(
        description="工业级日志预处理：source_file/*.log -> 结构化 + 故障窗口片段 + log_index + fault_index"
    )
    parser.add_argument("--file", "-f", type=str, default=None, help="只处理指定文件名（含后缀）")
    parser.add_argument("--before", type=int, default=FAULT_WINDOW_SECONDS_BEFORE, help="故障窗口锚点前秒数")
    parser.add_argument("--after", type=int, default=FAULT_WINDOW_SECONDS_AFTER, help="故障窗口锚点后秒数")
    parser.add_argument("--gap", type=int, default=FAULT_MERGE_GAP_SECONDS, help="合并间隔阈值(秒)，超过此间隔不合并、另起新段")
    args = parser.parse_args()

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    pre = LogPreprocessor(
        window_seconds_before=args.before,
        window_seconds_after=args.after,
        merge_gap_seconds=args.gap,
    )
    log_files = pre._collect_log_files()
    if args.file:
        log_files = [p for p in log_files if p.name == args.file]
    if not log_files:
        print(f"未找到日志文件：{SOURCE_DIR}（后缀: {LOG_SUFFIXES | TEXT_SUFFIXES}）")
        raise SystemExit(1)

    print("=" * 80)
    print("phase1_preprocess_log：日志解析 -> 结构化 -> 故障检测与故障窗口 -> 索引")
    print("=" * 80)
    print(f"SOURCE_DIR: {SOURCE_DIR}")
    print(f"LOG_CACHE: {LOG_CACHE_DIR}, STRUCTURED: {pre.structured_dir}, FAULT_WINDOWS: {pre.fault_windows_dir}")
    print(f"故障窗口: 锚点前 {pre.window_seconds_before}s, 锚点后 {pre.window_seconds_after}s, 合并间隔阈值 {pre.merge_gap_seconds}s")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    for i, log_path in enumerate(log_files, 1):
        print(f"\n[{i}/{len(log_files)}] {log_path.name}")
        res = pre.process_one_log_file(log_path)
        results.append(res)
        if res.get("error"):
            print(f"  错误: {res['error']}")
        else:
            n_seg = len(res.get("segments") or [])
            if n_seg == 0:
                print(f"  记录: {res.get('records', 0)}, 无锚点(已忽略，不写 fault_windows、不进入映射)")
            else:
                print(f"  记录: {res.get('records', 0)}, 故障窗口片段: {n_seg}, case_key: {res.get('case_key', '')}")

    index = pre.build_log_index(results)
    index_path = LOG_CACHE_DIR / LOG_INDEX_FILENAME
    LOG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 log_index: {index_path}（{len(index)} 个 case_key）")

    fault_index = pre.build_fault_index(results)
    fault_index_path = LOG_CACHE_DIR / FAULT_INDEX_FILENAME
    fault_index_path.write_text(json.dumps(fault_index, ensure_ascii=False, indent=2), encoding="utf-8")
    n_cases = len(fault_index.get("by_case_id") or {})
    n_devices = len(fault_index.get("by_device_sn") or {})
    print(f"已写入 fault_index: {fault_index_path}（by_case_id: {n_cases}, by_device_sn: {n_devices}）")
    print("phase1_preprocess_log 完成。")

    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase1_log",
            script="phase1_preprocess_log.py",
            status="success",
            files_processed=len(log_files),
            detail={"log_index_count": len(index), "by_case_id": n_cases, "by_device_sn": n_devices},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    try:
        main()
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        try:
            from pipeline_run_logger import append_run_record
            append_run_record(step_id="phase1_log", script="phase1_preprocess_log.py", status="failed", error=str(e))
        except Exception:
            pass
        raise
