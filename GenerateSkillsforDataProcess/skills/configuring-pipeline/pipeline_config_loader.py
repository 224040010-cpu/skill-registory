"""
pipeline_config_loader.py
加载 pipeline_config.json，解析 ${base_dir} 变量，确保目录存在。

本文件位于 skills/configuring-pipeline/，与 pipeline_config.json 同目录。

用法:
    from pipeline_config_loader import load_config

    config = load_config()
    raw_dir = config["input"]["raw_material"]       # 已解析为绝对路径
    md_dir  = config["intermediate"]["markdown"]     # 已解析为绝对路径
"""

import json
import os
import re
from pathlib import Path
from typing import Optional, Union

_CONFIG_FILENAME = "pipeline_config.json"


def _find_config_file() -> Path:
    """从当前文件所在目录向上查找 pipeline_config.json（优先同目录）"""
    search = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = search / _CONFIG_FILENAME
        if candidate.exists():
            return candidate
        search = search.parent
    raise FileNotFoundError(
        f"找不到 {_CONFIG_FILENAME}，请确认文件在 skills/configuring-pipeline 目录下"
    )


def _resolve_vars(obj, variables: dict):
    """递归替换 ${var} 占位符"""
    if isinstance(obj, str):
        def replacer(m):
            key = m.group(1)
            return variables.get(key, m.group(0))
        return re.sub(r"\$\{(\w+)\}", replacer, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_vars(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_vars(v, variables) for v in obj]
    return obj


def _resolve_env(obj):
    """递归替换 ${env:VAR} 为环境变量值；未设置时替换为空字符串（便于脚本用 or default）"""
    if isinstance(obj, str):
        def replacer(m):
            var_name = m.group(1)
            return os.environ.get(var_name, "")
        return re.sub(r"\$\{env:(\w+)\}", replacer, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env(v) for v in obj]
    return obj


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    ensure_dirs: bool = True,
) -> dict:
    """
    加载并解析配置文件。

    参数:
        config_path: 自定义配置文件路径，None 则自动查找
        ensure_dirs:  True 时自动创建 intermediate 和 output 中的所有目录

    返回:
        解析后的配置字典，所有路径为绝对路径字符串
    """
    if config_path is None:
        config_path = _find_config_file()
    else:
        config_path = Path(config_path)

    # 配置内路径（base_dir、input、output 等）相对项目根解析；本文件在 skills/configuring-pipeline/ 故 parents[2]=根
    config_dir = config_path.resolve().parent
    project_root = config_dir.parents[1]  # config 在 skills/configuring-pipeline/ -> 项目根

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 构建变量表
    variables = {"base_dir": raw.get("base_dir", "data_prepare")}

    # 解析 ${base_dir} 等变量
    config = _resolve_vars(raw, variables)
    # 解析 ${env:VAR} 环境变量（如 UNSTRUCTURED_API_KEY）
    config = _resolve_env(config)

    # 将所有路径转为绝对路径（相对 config 文件所在目录）
    for section_key in ("input", "intermediate", "output"):
        section = config.get(section_key, {})
        for key, val in section.items():
            if key.startswith("_"):
                continue
            abs_path = str((project_root / val).resolve())
            section[key] = abs_path

    # 自动创建目录（output 中若为文件路径如 .jsonl 则只创建其父目录）
    if ensure_dirs:
        for section_key in ("intermediate", "output"):
            section = config.get(section_key, {})
            for key, val in section.items():
                if key.startswith("_"):
                    continue
                p = Path(val)
                if p.suffix:
                    p.parent.mkdir(parents=True, exist_ok=True)
                else:
                    os.makedirs(val, exist_ok=True)

    return config


if __name__ == "__main__":
    cfg = load_config()
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
