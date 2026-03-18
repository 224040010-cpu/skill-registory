"""
脚本：phase0_sort_files.py

用途：
将 `data_prepare/raw_material` 下按“知识层子文件夹”组织的原始文件，整理到
`data_prepare/source_file` 下，供 phase1 统一读取。

规则：

1. 遍历 `raw_material` 下的一级子文件夹，例如：
   - `raw_material/memory_case/`
   - `raw_material/normative/`
   - `raw_material/evidence/`

2. 若知识层子文件夹下是“单文件”：
   - 直接复制到对应的 `source_file/<knowledge_layer>/` 下
   - 文件名保持不变

   示例：
   `raw_material/memory_case/xxx.pdf`
   ->
   `source_file/memory_case/xxx.pdf`

3. 若知识层子文件夹下是“案例文件夹”：
   - 递归遍历该文件夹中的所有文件
   - 将“案例文件夹名”加到每个文件名前面
   - 再复制到对应的 `source_file/<knowledge_layer>/` 下

   示例：
   `raw_material/memory_case/XXXcase/表格文件.xls`
   ->
   `source_file/memory_case/XXXcase表格文件.xls`

4. 为避免覆盖：
   - 若目标文件已存在，则自动追加 `__dupN`

注意：
- 本脚本默认使用复制 `copy2`，不删除 `raw_material` 中原始文件
- 输出目录保留“知识层”这一层，不再保留案例子文件夹层级
"""

from __future__ import annotations

import shutil
from pathlib import Path


import sys as _sys
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

try:
    from pipeline_config_loader import load_config as _load_config
    _cfg = _load_config(ensure_dirs=True)
    RAW_MATERIAL_DIR = Path(_cfg["input"]["raw_material"])
    SOURCE_FILE_DIR = Path(_cfg["intermediate"]["source_file"])
    DATA_PREPARE_DIR = RAW_MATERIAL_DIR.parent
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    RAW_MATERIAL_DIR = DATA_PREPARE_DIR / "raw_material"
    SOURCE_FILE_DIR = DATA_PREPARE_DIR / "source_file"

# 校验：raw_material 下必须存在这五个知识层子文件夹，否则不继续
REQUIRED_KNOWLEDGE_LAYERS = ("derived_index", "evidence", "memory_case", "memory_rule", "normative")


def _validate_raw_material_structure() -> None:
    """
    校验 base_dir/raw_material 存在，且其下必须存在 derived_index, evidence, memory_case,
    memory_rule, normative 五个子文件夹；缺一则报错并退出，流程不继续。
    """
    if not RAW_MATERIAL_DIR.exists():
        print(f"✗ raw_material 不存在: {RAW_MATERIAL_DIR}")
        raise SystemExit(1)
    if not RAW_MATERIAL_DIR.is_dir():
        print(f"✗ raw_material 不是目录: {RAW_MATERIAL_DIR}")
        raise SystemExit(1)
    existing = {p.name for p in RAW_MATERIAL_DIR.iterdir() if p.is_dir()}
    missing = [k for k in REQUIRED_KNOWLEDGE_LAYERS if k not in existing]
    if missing:
        print(f"✗ raw_material 下缺少以下知识层子文件夹: {missing}")
        print(f"  要求必须存在: {list(REQUIRED_KNOWLEDGE_LAYERS)}")
        print(f"  当前目录: {RAW_MATERIAL_DIR}")
        raise SystemExit(1)


def _safe_target_path(target_dir: Path, target_name: str) -> Path:
    """
    返回一个不会覆盖已有文件的目标路径。
    若同名，则自动追加 __dupN。
    """
    candidate = target_dir / target_name
    if not candidate.exists():
        return candidate

    stem = Path(target_name).stem
    suffix = Path(target_name).suffix
    i = 1
    while True:
        new_path = target_dir / f"{stem}__dup{i}{suffix}"
        if not new_path.exists():
            return new_path
        i += 1


def _copy_direct_files(layer_dir: Path, out_dir: Path) -> int:
    """
    复制知识层目录下的直接文件，文件名保持不变。
    """
    count = 0
    for p in sorted(layer_dir.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file():
            continue
        dst = _safe_target_path(out_dir, p.name)
        shutil.copy2(p, dst)
        count += 1
        print(f"[FILE] {p} -> {dst}")
    return count


def _copy_case_folder_files(layer_dir: Path, out_dir: Path) -> int:
    """
    复制知识层目录下的二级案例文件夹中的文件：
    - 递归遍历案例文件夹内的所有文件
    - 给每个文件名前加“案例文件夹名”
    - 输出到 source_file/<knowledge_layer>/ 下
    """
    count = 0
    for case_dir in sorted(layer_dir.iterdir(), key=lambda x: x.name.lower()):
        if not case_dir.is_dir():
            continue

        files = [f for f in case_dir.rglob("*") if f.is_file()]
        print(f"[CASE] {case_dir.name} | files={len(files)}")

        for src in sorted(files, key=lambda x: str(x).lower()):
            target_name = f"{case_dir.name}{src.name}"
            dst = _safe_target_path(out_dir, target_name)
            shutil.copy2(src, dst)
            count += 1
            print(f"       {src} -> {dst}")
    return count


def process_one_layer(layer_dir: Path) -> tuple[int, int]:
    """
    处理一个知识层目录，例如 raw_material/memory_case。

    Returns:
        (direct_file_count, case_folder_file_count)
    """
    out_dir = SOURCE_FILE_DIR / layer_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    direct_count = _copy_direct_files(layer_dir, out_dir)
    case_count = _copy_case_folder_files(layer_dir, out_dir)
    return direct_count, case_count


def main() -> None:
    _validate_raw_material_structure()

    SOURCE_FILE_DIR.mkdir(parents=True, exist_ok=True)

    layer_dirs = [p for p in sorted(RAW_MATERIAL_DIR.iterdir(), key=lambda x: x.name.lower()) if p.is_dir()]
    assert layer_dirs, "校验已通过则五种子目录必存在"

    print("=" * 80)
    print("phase0_sort_files: raw_material -> source_file")
    print(f"RAW_MATERIAL_DIR: {RAW_MATERIAL_DIR}")
    print(f"SOURCE_FILE_DIR : {SOURCE_FILE_DIR}")
    print(f"知识层目录数: {len(layer_dirs)}")
    print("=" * 80)

    total_direct = 0
    total_case = 0
    by_category = {}

    for layer_dir in layer_dirs:
        print(f"\n{'*' * 80}")
        print(f"处理知识层: {layer_dir.name}")
        print(f"{'*' * 80}")
        direct_count, case_count = process_one_layer(layer_dir)
        total_direct += direct_count
        total_case += case_count
        by_category[layer_dir.name] = direct_count + case_count
        print(f"  直接文件复制数: {direct_count}")
        print(f"  案例文件夹文件复制数: {case_count}")

    total_files = total_direct + total_case
    print("\n" + "=" * 80)
    print("完成")
    print(f"直接文件复制总数: {total_direct}")
    print(f"案例文件夹文件复制总数: {total_case}")
    print("=" * 80)

    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase0",
            script="phase0_sort_files.py",
            status="success",
            files_processed=total_files,
            detail={"direct": total_direct, "case_folder": total_case, "by_category": by_category},
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
            append_run_record(
                step_id="phase0",
                script="phase0_sort_files.py",
                status="failed",
                error=str(e),
            )
        except Exception:
            pass
        raise

