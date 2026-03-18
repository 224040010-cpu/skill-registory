from __future__ import annotations

"""
common_schema.py

这个文件的定位不是“处理 PDF / 日志 / 表格”的业务脚本，而是 data_prepare 流水线的公共数据模型层。

它解决的是三个问题：
1. 不同 phase 脚本产物字段命名不统一的问题
2. manifest / 资产治理需要统一对象结构的问题
3. 为后续“案例记忆 / 专家规则 / 审核状态 / 持续增量上传”预留统一字段的问题

当前它主要被 build_manifest.py 使用，用来：
- 定义统一资产记录 AssetRecord
- 生成稳定的 asset_id
- 生成 version
- 统一 knowledge_layer / asset_type / review_status 等枚举

后续当 phase1 / phase2 / phase3 脚本开始逐步改造时，也应该复用本文件里的：
- build_asset_record()
- make_asset_id()
- normalize_path()
- now_iso()

也就是说：
- 现在它先服务“资产盘点”
- 下一步它会逐步服务“脚本直接产出统一字段”
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence


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
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"


# 资产类型：
# 用来表达“这是什么对象”，强调对象在流水线中的身份，而不是仅仅表达文件后缀。
# 例如：
# - source_file：原始输入文件
# - document_processed：phase1 之后的文档标准化结果
# - qa_dataset / semantic_dataset：phase2 生成的衍生检索对象
# - memory_case / memory_rule：为后续记忆分层预留
ASSET_TYPES = {
    "source_file",
    "document_processed",
    "table_csv",
    "log_structured",
    "log_fault_window_index",
    "log_fault_window_segment",
    "qa_dataset",
    "semantic_dataset",
    "image_asset",
    "memory_case",
    "memory_rule",
}

# 知识分层：
# 用来表达“这个对象属于哪一层知识”。
# 注意它和 asset_type 不同：
# - asset_type 是对象身份
# - knowledge_layer 是知识语义归属
# 例如同样是 qa_dataset，也可能来自 normative 文档或未来 case memory。
KNOWLEDGE_LAYERS = {
    "normative",
    "evidence",
    "memory_case",
    "memory_rule",
    "derived_index",
}

# 对象由哪个阶段产出。
# 这不是业务状态，而是流水线阶段标签，便于排查对象来源。
PIPELINE_STAGES = {
    "phase0",
    "phase1",
    "phase2",
    "phase3",
    "memory",
    "manifest",
}

# 资产当前状态，偏系统可用性语义。
STATUSES = {
    "ready",
    "pending",
    "failed",
    "deleted",
}

# 审核状态，主要为未来 memory_case / memory_rule 预留。
# 一期虽然还没用审核流，但 schema 先保留这个字段，避免后续返工。
REVIEW_STATUSES = {
    "system_generated",
    "draft",
    "reviewed",
    "approved",
    "deprecated",
}


def now_iso() -> str:
    """统一生成 UTC ISO 时间字符串。"""
    return datetime.now(timezone.utc).isoformat()


def normalize_path(path: str | Path | None, *, base_dir: Path = DATA_PREPARE_DIR) -> str:
    """
    统一路径表达，尽量转为相对 data_prepare 的稳定路径。

    为什么要这样做：
    - 避免绝对路径导致不同机器上 asset_id 不稳定
    - 让 manifest 中的路径更短、更可读
    - 便于后续增量上传和跨环境对比
    """
    if path is None:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(base_dir.resolve()).as_posix()
    except Exception:
        try:
            return p.relative_to(base_dir).as_posix()
        except Exception:
            return str(p).replace("\\", "/")


def sha1_text(text: str) -> str:
    """对字符串内容做 SHA1，常用于生成稳定短标识。"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sha1_file(path: str | Path) -> str:
    """
    对文件内容做 SHA1。

    用途：
    - 作为 version 的基础
    - 用于判断“同一个 asset 是否发生内容变化”
    """
    file_path = Path(path)
    h = hashlib.sha1()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_asset_id(asset_type: str, storage_path: str | Path) -> str:
    """
    生成稳定 asset_id。

    当前规则：
    asset_id = hash(asset_type + normalized storage_path)

    语义上代表：
    - 这是“哪个逻辑对象”
    - 不代表对象内容版本

    也就是说：
    - 同一个路径上的同类对象，asset_id 固定
    - 内容变了，应该更新 version，而不是变更 asset_id
    """
    normalized = normalize_path(storage_path)
    return f"{asset_type}:{sha1_text(f'{asset_type}|{normalized}')[:24]}"


def _json_safe(value: Any) -> Any:
    """把 Path / set / tuple 等对象转换成适合 JSON 持久化的形式。"""
    if isinstance(value, Path):
        return normalize_path(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return value


def _validate_choice(field_name: str, value: str, choices: set[str]) -> None:
    """统一做枚举校验，避免脏值进入 manifest。"""
    if value not in choices:
        raise ValueError(f"{field_name}={value!r} 不在允许范围内: {sorted(choices)}")


@dataclass
class AssetRecord:
    """
    统一资产对象。

    顶层字段分成几类：
    1. 身份字段：asset_id / asset_type / knowledge_layer
    2. 路径与来源字段：source_path / storage_path / parent_asset_id
    3. 版本字段：version / created_at / updated_at
    4. 治理字段：status / is_source_of_truth / review_status / updated_by
    5. 扩展字段：tags / stats / attributes

    设计原则：
    - 顶层字段尽量少且稳定
    - 统计信息放 stats
    - 对象专属字段放 attributes
    - 不把所有字段都铺平，避免重复
    """
    asset_id: str
    asset_type: str
    knowledge_layer: str
    display_name: str
    source_name: str
    source_path: str
    storage_path: str
    parent_asset_id: str | None = None
    version: str = ""
    created_at: str = ""
    updated_at: str = ""
    pipeline_stage: str = ""
    status: str = "ready"
    is_source_of_truth: bool = True
    review_status: str = "system_generated"
    updated_by: str = "pipeline"
    tags: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转成可安全写入 json/jsonl 的 dict。"""
        return _json_safe(asdict(self))


def build_asset_record(
    *,
    asset_type: str,
    knowledge_layer: str,
    display_name: str,
    source_name: str,
    source_path: str | Path | None,
    storage_path: str | Path,
    parent_asset_id: str | None = None,
    version: str = "",
    created_at: str | None = None,
    updated_at: str | None = None,
    pipeline_stage: str,
    status: str = "ready",
    is_source_of_truth: bool = True,
    review_status: str = "system_generated",
    updated_by: str = "pipeline",
    tags: Sequence[str] | None = None,
    stats: Mapping[str, Any] | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> AssetRecord:
    """
    统一构造 AssetRecord 的入口。

    这个函数后续应该成为 phase1 / phase2 / phase3 脚本接入 common_schema 的主要方式。
    各处理脚本只负责整理自己的业务字段，然后统一通过本函数生成资产对象。
    """
    _validate_choice("asset_type", asset_type, ASSET_TYPES)
    _validate_choice("knowledge_layer", knowledge_layer, KNOWLEDGE_LAYERS)
    _validate_choice("pipeline_stage", pipeline_stage, PIPELINE_STAGES)
    _validate_choice("status", status, STATUSES)
    _validate_choice("review_status", review_status, REVIEW_STATUSES)

    normalized_storage_path = normalize_path(storage_path)
    normalized_source_path = normalize_path(source_path)
    record = AssetRecord(
        asset_id=make_asset_id(asset_type, normalized_storage_path),
        asset_type=asset_type,
        knowledge_layer=knowledge_layer,
        display_name=(display_name or "").strip(),
        source_name=(source_name or "").strip(),
        source_path=normalized_source_path,
        storage_path=normalized_storage_path,
        parent_asset_id=parent_asset_id,
        version=version,
        created_at=created_at or now_iso(),
        updated_at=updated_at or now_iso(),
        pipeline_stage=pipeline_stage,
        status=status,
        is_source_of_truth=is_source_of_truth,
        review_status=review_status,
        updated_by=updated_by,
        tags=[str(t).strip() for t in (tags or []) if str(t).strip()],
        stats=dict(_json_safe(dict(stats or {}))),
        attributes=dict(_json_safe(dict(attributes or {}))),
    )
    return record


def with_manifest_event(record: AssetRecord | Mapping[str, Any], *, manifest_op: str = "upsert") -> dict[str, Any]:
    """
    给资产对象包一层 manifest 事件字段。

    这样 manifest 不只是“当前状态快照”，也可以作为 append-only 的事件流使用。
    当前一期主要用 upsert，后续可扩展 delete。
    """
    if manifest_op not in {"upsert", "delete"}:
        raise ValueError(f"manifest_op={manifest_op!r} 不支持")
    payload = record.to_dict() if isinstance(record, AssetRecord) else dict(record)
    payload["manifest_op"] = manifest_op
    payload["manifest_emitted_at"] = now_iso()
    return payload


def merge_preserving_created_at(
    current: AssetRecord,
    previous: Mapping[str, Any] | None,
) -> AssetRecord:
    """
    当同一个 asset_id 已经存在旧记录时，保留其 created_at。

    目的：
    - asset 更新版本时，不要把“首次出现时间”覆盖掉
    - updated_at 代表本次刷新时间
    """
    if previous and previous.get("created_at"):
        current.created_at = str(previous["created_at"])
    return current


def stable_version_from_mapping(data: Mapping[str, Any]) -> str:
    """
    对内存中的结构化对象生成稳定 version。

    适用场景：
    - 不是直接落在单个文件里的对象
    - 或未来 memory_case / memory_rule 这类逻辑对象
    """
    canonical = json.dumps(_json_safe(dict(data)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha1_text(canonical)


def infer_layer_from_suffix(path: str | Path) -> str:
    """
    根据文件后缀做一个简化版知识分层推断。

    注意：
    - 这是一期的兜底策略，只适合 source_file 这类粗分层
    - 真正稳定的 knowledge_layer，后续应由具体处理脚本明确指定
    """
    suffix = Path(path).suffix.lower()
    if suffix in {".pdf", ".md"}:
        return "normative"
    if suffix in {".log", ".txt", ".jsonl", ".csv", ".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return "evidence"
    return "derived_index"


def infer_layer_from_source_tree(path: str | Path, source_root: str | Path) -> str:
    """
    优先根据 source_file 下第一层文件夹名识别 knowledge_layer。

    目标场景：
    data_prepare/source_file/
      normative/
      evidence/
      memory_case/
      memory_rule/
      derived_index/

    规则：
    1. 如果文件位于 source_root 的某个一级子目录下，且子目录名属于 KNOWLEDGE_LAYERS，
       则直接使用该目录名。
    2. 否则回退到 infer_layer_from_suffix()。

    这样可以兼容两种模式：
    - 老模式：source_file 下平铺文件
    - 新模式：source_file 下按知识层分文件夹
    """
    try:
        p = Path(path).resolve()
        root = Path(source_root).resolve()
        rel = p.relative_to(root)
        if len(rel.parts) >= 2:
            first_dir = rel.parts[0].strip()
            if first_dir in KNOWLEDGE_LAYERS:
                return first_dir
    except Exception:
        pass
    return infer_layer_from_suffix(path)

