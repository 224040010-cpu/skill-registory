"""
展示当前流水线配置摘要（解析后的路径与策略），供「确认后再执行」流程使用。
由 configuring-pipeline skill 通过 data-pipeline-mcp:run_script 调用，输出贴给用户确认。

用法（在项目根或 MCP 调用）:
    python scripts/show_pipeline_config.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 本脚本在 skills/configuring-pipeline/scripts/ 下，项目根 = parents[3]；loader/logger 在同 skill 根下
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

def main() -> None:
    try:
        from pipeline_config_loader import load_config
        cfg = load_config(ensure_dirs=False)
    except Exception as e:
        print(f"[错误] 无法加载配置: {e}")
        sys.exit(1)

    out = []
    out.append("========== 当前流水线配置摘要 ==========")
    out.append("")
    # 运行时环境
    conda_env = (cfg.get("conda_env") or "").strip()
    out.append(f"  conda_env: {conda_env if conda_env else '(未设置，使用当前环境)'}")
    out.append("")
    # 路径
    base = cfg.get("base_dir") or "(未设置)"
    out.append(f"  base_dir: {base}")
    inp = cfg.get("input") or {}
    raw = inp.get("raw_material", "(未设置)")
    out.append(f"  raw_material: {raw}")
    out.append("")
    inter = cfg.get("intermediate") or {}
    out.append("  intermediate 路径:")
    for k, v in inter.items():
        if k.startswith("_"):
            continue
        out.append(f"    {k}: {v}")
    out.append("")
    output = cfg.get("output") or {}
    out.append("  output 路径:")
    for k, v in output.items():
        if k.startswith("_"):
            continue
        out.append(f"    {k}: {v}")
    out.append("")
    # 向量化策略
    vec = cfg.get("vectorizing") or {}
    chroma = vec.get("chromadb") or {}
    hippo = vec.get("hipporag") or {}
    out.append("  向量化策略（默认增量，不重建）:")
    out.append(f"    chromadb.rebuild: {chroma.get('rebuild', False)}")
    out.append(f"    hipporag.rebuild: {hippo.get('rebuild', False)}")
    out.append("")
    out.append("==========================================")
    print("\n".join(out))

if __name__ == "__main__":
    main()
