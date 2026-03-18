"""
按「键路径 + 值」更新 pipeline_config.json 中的一项，供自然语言修改配置后由 Agent 通过
data-pipeline-mcp:run_script 调用，避免手改 JSON 出错。

用法:
    python scripts/apply_config_change.py <key_path> <value>
    python scripts/apply_config_change.py base_dir data2
    python scripts/apply_config_change.py vectorizing.chromadb.rebuild true

支持键路径见 references/natural-language-config-keys.md；value 为字符串，布尔会自动转换 true/false。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 项目根 = parents[3]；配置与本 skill 同目录
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _PROJECT_ROOT / "skills" / "configuring-pipeline" / "pipeline_config.json"


def _set_nested(d: dict, key_path: str, value: str) -> None:
    parts = key_path.strip().split(".")
    current = d
    for i, p in enumerate(parts[:-1]):
        if p not in current:
            current[p] = {}
        current = current[p]
        if not isinstance(current, dict):
            raise ValueError(f"键路径 {key_path} 在 '{p}' 处不是对象")
    last = parts[-1]
    # 尝试类型转换
    if value.lower() in ("true", "yes", "1"):
        current[last] = True
    elif value.lower() in ("false", "no", "0"):
        current[last] = False
    elif value.isdigit():
        current[last] = int(value)
    else:
        current[last] = value


def main() -> None:
    if len(sys.argv) < 3:
        print("用法: apply_config_change.py <key_path> <value>")
        print("示例: apply_config_change.py base_dir data2")
        print("      apply_config_change.py vectorizing.chromadb.rebuild false")
        sys.exit(1)
    key_path = sys.argv[1]
    value = sys.argv[2]

    if not _CONFIG_PATH.exists():
        print(f"[错误] 配置文件不存在: {_CONFIG_PATH}")
        sys.exit(1)

    try:
        raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[错误] 读取 JSON 失败: {e}")
        sys.exit(1)

    try:
        _set_nested(raw, key_path, value)
    except Exception as e:
        print(f"[错误] 设置键失败: {e}")
        sys.exit(1)

    try:
        _CONFIG_PATH.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[错误] 写入文件失败: {e}")
        sys.exit(1)

    print(f"已更新: {key_path} = {value}")
    print("建议运行 show_pipeline_config.py 展示当前配置供用户确认。")


if __name__ == "__main__":
    main()
