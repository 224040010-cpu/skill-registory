from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from common_schema import (
    DATA_PREPARE_DIR,
    PROCESSED_DATA_DIR,
    AssetRecord,
    build_asset_record,
    infer_layer_from_source_tree,
    make_asset_id,
    merge_preserving_created_at,
    now_iso,
    normalize_path,
    sha1_file,
    with_manifest_event,
)

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
    MANIFEST_DIR = Path(_cfg["output"]["manifests"])
    SOURCE_MANIFEST_PATH = MANIFEST_DIR / "source_manifest.jsonl"
    INDEX_MANIFEST_PATH = MANIFEST_DIR / "index_manifest.jsonl"
    SOURCE_FILE_DIR = Path(_cfg["intermediate"]["source_file"])
    MARKDOWN_DIR = Path(_cfg["intermediate"]["markdown"])
    TABLE_CACHE_DIR = Path(_cfg["intermediate"]["table_cache"])
    LOG_CACHE_DIR = Path(_cfg["intermediate"]["log_cache"])
    STRUCTURED_LOG_DIR = LOG_CACHE_DIR / "structured"
    FAULT_WINDOWS_DIR = LOG_CACHE_DIR / "fault_windows"
    QA_PAIR_DIR = Path(_cfg["intermediate"]["qa_pair"])
    SEMANTIC_CHUNK_DIR = Path(_cfg["intermediate"]["semantic_chunk"])
    IMAGES_DIR = Path(_cfg["intermediate"]["images"])
except Exception:
    MANIFEST_DIR = PROCESSED_DATA_DIR / "manifests"
    SOURCE_MANIFEST_PATH = MANIFEST_DIR / "source_manifest.jsonl"
    INDEX_MANIFEST_PATH = MANIFEST_DIR / "index_manifest.jsonl"
    SOURCE_FILE_DIR = DATA_PREPARE_DIR / "source_file"
    MARKDOWN_DIR = PROCESSED_DATA_DIR / "markdown"
    TABLE_CACHE_DIR = PROCESSED_DATA_DIR / "table_cache"
    LOG_CACHE_DIR = PROCESSED_DATA_DIR / "log_cache"
    STRUCTURED_LOG_DIR = LOG_CACHE_DIR / "structured"
    FAULT_WINDOWS_DIR = LOG_CACHE_DIR / "fault_windows"
    QA_PAIR_DIR = PROCESSED_DATA_DIR / "qa_pair"
    SEMANTIC_CHUNK_DIR = PROCESSED_DATA_DIR / "semantic_chunk"
    IMAGES_DIR = PROCESSED_DATA_DIR / "images"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sidecar_path(path: Path) -> Path:
    return path.with_name(path.name + ".asset_meta.json")


def _read_sidecar(path: Path) -> dict[str, Any]:
    sidecar = _sidecar_path(path)
    if not sidecar.exists():
        return {}
    try:
        return _read_json(sidecar)
    except Exception:
        return {}


def _load_latest_manifest_records(manifest_path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not manifest_path.exists():
        return latest
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            asset_id = str(record.get("asset_id") or "").strip()
            if not asset_id:
                continue
            latest[asset_id] = record
    return latest


def _append_changed_records(manifest_path: Path, records: Iterable[AssetRecord], *, dry_run: bool = False) -> tuple[int, int]:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    latest = _load_latest_manifest_records(manifest_path)
    appended = 0
    skipped = 0
    lines_to_append: list[str] = []

    for record in records:
        previous = latest.get(record.asset_id)
        record = merge_preserving_created_at(record, previous)
        if previous and previous.get("version") == record.version:
            skipped += 1
            continue
        payload = with_manifest_event(record, manifest_op="upsert")
        lines_to_append.append(json.dumps(payload, ensure_ascii=False))
        appended += 1

    if lines_to_append and not dry_run:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in lines_to_append:
                f.write(line)
                f.write("\n")

    return appended, skipped


def _iter_source_file_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not SOURCE_FILE_DIR.exists():
        return records
    for file_path in sorted(p for p in SOURCE_FILE_DIR.rglob("*") if p.is_file()):
        rel = normalize_path(file_path)
        records.append(
            build_asset_record(
                asset_type="source_file",
                knowledge_layer=infer_layer_from_source_tree(file_path, SOURCE_FILE_DIR),
                display_name=file_path.name,
                source_name=file_path.name,
                source_path=rel,
                storage_path=rel,
                version=sha1_file(file_path),
                pipeline_stage="phase0",
                is_source_of_truth=True,
                stats={
                    "size_bytes": file_path.stat().st_size,
                },
                attributes={
                    "suffix": file_path.suffix.lower(),
                },
            )
        )
    return records


def _iter_document_processed_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not MARKDOWN_DIR.exists():
        return records
    for path in sorted(MARKDOWN_DIR.glob("*_processed.json")):
        data = _read_json(path)
        meta = data.get("metadata") or {}
        asset_meta = data.get("asset_meta") or {}
        source_path = meta.get("source_path") or ""
        parent_asset_id = make_asset_id("source_file", source_path) if source_path else None
        rel_path = normalize_path(path)
        records.append(
            build_asset_record(
                asset_type="document_processed",
                knowledge_layer=asset_meta.get("knowledge_layer") or "normative",
                display_name=meta.get("source") or path.stem.replace("_processed", ""),
                source_name=meta.get("source_raw") or path.stem.replace("_processed", ""),
                source_path=source_path,
                storage_path=rel_path,
                parent_asset_id=parent_asset_id,
                version=sha1_file(path),
                created_at=meta.get("processed_at"),
                updated_at=meta.get("processed_at") or now_iso(),
                pipeline_stage="phase1",
                is_source_of_truth=True,
                stats={
                    "section_count": meta.get("section_count", 0),
                    "image_count": meta.get("image_count", 0),
                    "reference_count": meta.get("reference_count", 0),
                    "total_chars": meta.get("total_chars", 0),
                },
                attributes={
                    "markdown_path": meta.get("markdown_path"),
                    "images_dir": meta.get("images_dir"),
                    "table_placeholder_count": meta.get("table_placeholder_count", 0),
                    "table_summary_count": meta.get("table_summary_count", 0),
                    "table_file_count": meta.get("table_file_count", 0),
                    "pdf_annotation_link_count": meta.get("pdf_annotation_link_count", 0),
                },
            )
        )
    return records


def _iter_table_csv_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not TABLE_CACHE_DIR.exists():
        return records
    for path in sorted(TABLE_CACHE_DIR.glob("*.csv")):
        rel_path = normalize_path(path)
        sidecar = _read_sidecar(path)
        records.append(
            build_asset_record(
                asset_type="table_csv",
                knowledge_layer=sidecar.get("knowledge_layer") or "evidence",
                display_name=sidecar.get("display_name") or path.name,
                source_name=sidecar.get("source_name") or path.stem,
                source_path=sidecar.get("source_path") or rel_path,
                storage_path=rel_path,
                version=sha1_file(path),
                created_at=sidecar.get("created_at"),
                updated_at=sidecar.get("updated_at"),
                pipeline_stage=sidecar.get("pipeline_stage") or "phase1",
                is_source_of_truth=sidecar.get("is_source_of_truth", True),
                stats={
                    "size_bytes": path.stat().st_size,
                },
                attributes={
                    "sheet_name": sidecar.get("attributes", {}).get("sheet_name", ""),
                    "origin_excel_path": sidecar.get("attributes", {}).get("origin_excel_path", ""),
                    "suffix": ".csv",
                },
            )
        )
    return records


def _iter_log_structured_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not STRUCTURED_LOG_DIR.exists():
        return records
    for path in sorted(STRUCTURED_LOG_DIR.glob("*.jsonl")):
        rel_path = normalize_path(path)
        sidecar = _read_sidecar(path)
        source_path = sidecar.get("source_path") or rel_path
        records.append(
            build_asset_record(
                asset_type="log_structured",
                knowledge_layer=sidecar.get("knowledge_layer") or "evidence",
                display_name=sidecar.get("display_name") or path.stem,
                source_name=sidecar.get("source_name") or path.stem,
                source_path=source_path,
                storage_path=rel_path,
                version=sha1_file(path),
                created_at=sidecar.get("created_at"),
                updated_at=sidecar.get("updated_at"),
                pipeline_stage=sidecar.get("pipeline_stage") or "phase1",
                is_source_of_truth=sidecar.get("is_source_of_truth", True),
                stats={
                    "size_bytes": path.stat().st_size,
                    "record_count": sidecar.get("stats", {}).get("record_count", 0),
                },
            )
        )
    return records


def _iter_log_fault_window_index_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not FAULT_WINDOWS_DIR.exists():
        return records
    for path in sorted(FAULT_WINDOWS_DIR.glob("*_fault_windows.json")):
        data = _read_json(path)
        rel_path = normalize_path(path)
        asset_meta = data.get("asset_meta") or {}
        source_stem = data.get("source_stem") or path.stem.replace("_fault_windows", "")
        parent_structured = data.get("source_jsonl") or ""
        parent_asset_id = make_asset_id("log_structured", parent_structured) if parent_structured else None
        records.append(
            build_asset_record(
                asset_type="log_fault_window_index",
                knowledge_layer=asset_meta.get("knowledge_layer") or "evidence",
                display_name=source_stem,
                source_name=source_stem,
                source_path=parent_structured,
                storage_path=rel_path,
                parent_asset_id=parent_asset_id,
                version=sha1_file(path),
                created_at=asset_meta.get("created_at"),
                updated_at=asset_meta.get("updated_at"),
                pipeline_stage=asset_meta.get("pipeline_stage") or "phase1",
                is_source_of_truth=asset_meta.get("is_source_of_truth", True),
                stats={
                    "window_count": len(data.get("fault_windows") or []),
                    "total_records": data.get("total_records", 0),
                },
                attributes={
                    "case_id": data.get("case_id", ""),
                    "case_key": data.get("case_key", ""),
                    "device_sn": data.get("device_sn", ""),
                    "window_seconds_before": data.get("window_seconds_before", 0),
                    "window_seconds_after": data.get("window_seconds_after", 0),
                    "merge_gap_seconds": data.get("merge_gap_seconds", 0),
                },
            )
        )
    return records


def _iter_log_fault_window_segment_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not FAULT_WINDOWS_DIR.exists():
        return records
    for path in sorted(FAULT_WINDOWS_DIR.glob("*_window_*.jsonl")):
        rel_path = normalize_path(path)
        parent_name = path.stem.rsplit("_window_", 1)[0] + "_fault_windows.json"
        parent_path = FAULT_WINDOWS_DIR / parent_name
        parent_asset_id = make_asset_id("log_fault_window_index", normalize_path(parent_path)) if parent_path.exists() else None
        records.append(
            build_asset_record(
                asset_type="log_fault_window_segment",
                knowledge_layer="evidence",
                display_name=path.stem,
                source_name=path.stem,
                source_path=rel_path,
                storage_path=rel_path,
                parent_asset_id=parent_asset_id,
                version=sha1_file(path),
                pipeline_stage="phase1",
                is_source_of_truth=True,
                stats={
                    "size_bytes": path.stat().st_size,
                },
            )
        )
    return records


def _iter_qa_dataset_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not QA_PAIR_DIR.exists():
        return records
    for path in sorted(QA_PAIR_DIR.glob("*.json")):
        if path.name.endswith(".metadata.json"):
            continue
        data = _read_json(path)
        meta = data.get("metadata") or {}
        asset_meta = data.get("asset_meta") or {}
        source_name = meta.get("source") or path.stem.replace("_qa", "")
        source_type = meta.get("source_type") or "document_qa"
        if source_type == "log_fault_segment":
            knowledge_layer = asset_meta.get("knowledge_layer") or "derived_index"
            parent_asset_id = make_asset_id("log_fault_window_index", f"processed_data/log_cache/fault_windows/{source_name}_fault_windows.json")
        else:
            knowledge_layer = asset_meta.get("knowledge_layer") or "derived_index"
            parent_asset_id = make_asset_id("document_processed", f"processed_data/markdown/{source_name}_processed.json")
        records.append(
            build_asset_record(
                asset_type="qa_dataset",
                knowledge_layer=knowledge_layer,
                display_name=source_name,
                source_name=source_name,
                source_path=meta.get("source_path") or "",
                storage_path=normalize_path(path),
                parent_asset_id=parent_asset_id,
                version=sha1_file(path),
                created_at=asset_meta.get("created_at"),
                updated_at=asset_meta.get("updated_at"),
                pipeline_stage=asset_meta.get("pipeline_stage") or "phase2",
                is_source_of_truth=asset_meta.get("is_source_of_truth", False),
                stats={
                    "qa_count": meta.get("total", 0),
                    "segment_count": meta.get("segment_count", 0),
                },
                attributes={
                    "source_type": source_type,
                },
            )
        )
    return records


def _iter_semantic_dataset_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not SEMANTIC_CHUNK_DIR.exists():
        return records
    for path in sorted(SEMANTIC_CHUNK_DIR.glob("*_for_chunking.json")):
        data = _read_json(path)
        meta = data.get("document_metadata") or {}
        asset_meta = data.get("asset_meta") or {}
        doc_name = meta.get("doc_name") or path.stem.replace("_for_chunking", "")
        source_type = meta.get("source_type") or ""
        source_path = meta.get("source_path") or ""
        if source_type == "table_csv":
            parent_asset_id = make_asset_id("table_csv", source_path)
        elif source_type == "log_fault_segment":
            parent_asset_id = make_asset_id("log_fault_window_index", f"processed_data/log_cache/fault_windows/{doc_name}_fault_windows.json")
        else:
            parent_asset_id = make_asset_id("document_processed", f"processed_data/markdown/{doc_name}_processed.json")
        records.append(
            build_asset_record(
                asset_type="semantic_dataset",
                knowledge_layer=asset_meta.get("knowledge_layer") or "derived_index",
                display_name=doc_name,
                source_name=doc_name,
                source_path=source_path,
                storage_path=normalize_path(path),
                parent_asset_id=parent_asset_id,
                version=sha1_file(path),
                created_at=asset_meta.get("created_at"),
                updated_at=asset_meta.get("updated_at"),
                pipeline_stage=asset_meta.get("pipeline_stage") or "phase2",
                is_source_of_truth=asset_meta.get("is_source_of_truth", False),
                stats={
                    "chunk_count": meta.get("chunk_count", 0),
                    "section_count": meta.get("section_count", 0),
                    "image_count": meta.get("image_count", 0),
                },
                attributes={
                    "source_type": source_type,
                    "markdown_path": meta.get("markdown_path", ""),
                },
            )
        )
    return records


def _iter_image_assets() -> list[AssetRecord]:
    records: list[AssetRecord] = []
    if not IMAGES_DIR.exists():
        return records
    for doc_dir in sorted(p for p in IMAGES_DIR.iterdir() if p.is_dir()):
        for image_path in sorted(p for p in doc_dir.iterdir() if p.is_file()):
            rel_path = normalize_path(image_path)
            doc_name = doc_dir.name
            parent_asset_id = make_asset_id("document_processed", f"processed_data/markdown/{doc_name}_processed.json")
            records.append(
                build_asset_record(
                    asset_type="image_asset",
                    knowledge_layer="derived_index",
                    display_name=image_path.name,
                    source_name=doc_name,
                    source_path=rel_path,
                    storage_path=rel_path,
                    parent_asset_id=parent_asset_id,
                    version=sha1_file(image_path),
                    pipeline_stage="phase1",
                    is_source_of_truth=False,
                    stats={
                        "size_bytes": image_path.stat().st_size,
                    },
                    attributes={
                        "doc_name": doc_name,
                        "suffix": image_path.suffix.lower(),
                    },
                )
            )
    return records


SOURCE_BUILDERS: list[Callable[[], list[AssetRecord]]] = [
    _iter_source_file_assets,
    _iter_document_processed_assets,
    _iter_table_csv_assets,
    _iter_log_structured_assets,
    _iter_log_fault_window_index_assets,
    _iter_log_fault_window_segment_assets,
]

INDEX_BUILDERS: list[Callable[[], list[AssetRecord]]] = [
    _iter_qa_dataset_assets,
    _iter_semantic_dataset_assets,
    _iter_image_assets,
]


def build_source_manifest(*, dry_run: bool = False) -> tuple[int, int]:
    records: list[AssetRecord] = []
    for builder in SOURCE_BUILDERS:
        records.extend(builder())
    return _append_changed_records(SOURCE_MANIFEST_PATH, records, dry_run=dry_run)


def build_index_manifest(*, dry_run: bool = False) -> tuple[int, int]:
    records: list[AssetRecord] = []
    for builder in INDEX_BUILDERS:
        records.extend(builder())
    return _append_changed_records(INDEX_MANIFEST_PATH, records, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="以追加模式构建 processed_data 全局 manifest")
    parser.add_argument(
        "--target",
        choices=["all", "source", "index"],
        default="all",
        help="构建 source manifest、index manifest 或两者都构建",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计新增/跳过数量，不真正写入 jsonl",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("build_manifest: append-only manifest builder")
    print(f"DATA_PREPARE_DIR : {DATA_PREPARE_DIR}")
    print(f"PROCESSED_DATA_DIR: {PROCESSED_DATA_DIR}")
    print(f"MANIFEST_DIR      : {MANIFEST_DIR}")
    print(f"MODE              : {args.target}")
    print(f"DRY_RUN           : {args.dry_run}")
    print("=" * 80)

    source_appended, source_skipped = 0, 0
    index_appended, index_skipped = 0, 0
    if args.target in {"all", "source"}:
        source_appended, source_skipped = build_source_manifest(dry_run=args.dry_run)
        print(f"[source_manifest] 新增 {source_appended} 条，跳过 {source_skipped} 条")

    if args.target in {"all", "index"}:
        index_appended, index_skipped = build_index_manifest(dry_run=args.dry_run)
        print(f"[index_manifest] 新增 {index_appended} 条，跳过 {index_skipped} 条")

    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="build_manifest",
            script="build_manifest.py",
            status="success",
            files_processed=source_appended + source_skipped + index_appended + index_skipped,
            detail={
                "target": args.target,
                "source_appended": source_appended,
                "source_skipped": source_skipped,
                "index_appended": index_appended,
                "index_skipped": index_skipped,
            },
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()

