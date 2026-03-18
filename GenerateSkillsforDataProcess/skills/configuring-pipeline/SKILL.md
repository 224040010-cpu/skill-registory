---
name: configuring-pipeline
bundle_scope: ops-agent
risk_level: L3
description: |
  Reads and updates data pipeline configuration (paths, AWS, Unstructured API, vectorizing strategy)
  and run log. Exposes scripts to show config summary and apply targeted config changes; executes the
  "show config → optional natural-language edit → user confirm → then proceed" flow before
  any data processing so that config is confirmed before phase0/phase1/... scripts run.
  Use when the user wants to change data paths, set rebuild/upsert, set API keys, view run
  history, or when the user says "跑数据处理"/"执行流水线" — then first complete config
  confirmation here; the Agent may then run phase scripts in separate steps.
  Do NOT use when the user has already confirmed config in this conversation and only asks
  to run a specific phase (e.g. "开始执行分拣") — route to the corresponding phase (e.g. sorting-raw-files) instead.
---

# Purpose

This is the single place for **config and run-log** and for **confirm-before-run**.
It owns:
- The **config confirmation flow**: show current config → allow natural-language edits →
  user confirms → then Agent may run phase scripts (sorting-raw-files, preprocessing-*, etc.).
- Scripts under **scripts/** to show config (`show_pipeline_config.py`) and apply one key
  change (`apply_config_change.py`), so all config-related behavior stays inside configuring-pipeline.
- References for which keys can be modified by natural language.

The three files (pipeline_config.json, pipeline_config_loader.py, pipeline_run_logger.py) live in
**this directory** (skills/configuring-pipeline/); other phase modules add this path to sys.path and
import load_config / append_run_record as before.

---

# Trigger

**Use when:**
- User says "跑数据处理" / "执行流水线" / "开始处理数据" → **先走本流程的确认步骤**，确认后再执行 phase 脚本
- User wants to change where data lives (e.g. base_dir, raw_material), set rebuild vs upsert, set API keys
- User asks to view pipeline run history or "上次跑到哪一步"
- User asks "pipeline_config 怎么改" / "运行记录在哪" / "先确认一下配置再跑"

**Do NOT use when:**
- User has **已在本轮对话中确认过配置**且明确只说「开始执行分拣/phase0」→ 直接用 sorting-raw-files 等执行
- User asks how a specific phase script works internally → point to that phase’s SKILL.md (e.g. sorting-raw-files, preprocessing-pdf-sources)

---

# Workflow

[ ] Step 1: 展示当前配置
    - 调用 `data-pipeline-mcp:run_script(script=scripts/show_pipeline_config.py, args=[])`
    - 将脚本输出的「当前流水线配置摘要」贴给用户（含 **conda_env**、base_dir、raw_material、output、vectorizing.rebuild 等），便于用户选择/确认运行环境后再执行

[ ] Step 2: 若用户用自然语言要求修改配置
    - 将用户意图映射为「键路径 + 值」（见 `references/natural-language-config-keys.md`）
    - 调用 `data-pipeline-mcp:run_script(script=scripts/apply_config_change.py, args=["<key_path>", "<value>"])` 或直接编辑本目录下的 pipeline_config.json（保持合法 JSON；路径见 references/where-are-the-three-files.md）
    - 修改后可再次调用 Step 1 的 run_script 展示更新后摘要

[ ] Step 3: 向用户确认
    - 明确询问：「是否按当前配置执行数据处理？确认后我将执行 phase0 分拣 / 后续步骤。」
    - 仅当用户回复确认（如「确认」「开始」「可以」「执行」）后，本流程结束；Agent 在**下一步**另行调用 `data-pipeline-mcp:run_script` 执行对应 phase 脚本，**不确认不执行**。若用户未确认则结束本流程，不执行任何 phase。

[ ] Step 4: 仅改配置或仅查看时，确定要改什么或只看什么（参数：key_path、value 等）
    - 运行环境：conda_env（执行 phase 脚本时使用的 conda 环境名）；路径：base_dir、input/intermediate/output；策略：vectorizing.chromadb.rebuild 等；运行记录：仅查看

[ ] Step 5: 改配置
    - 调用 `data-pipeline-mcp:run_script(script=scripts/apply_config_change.py, args=["<key_path>", "<value>"])` 或直接编辑 pipeline_config.json；敏感项用 "${env:VAR}"，提醒用户在环境中设置

[ ] Step 6: 查看运行记录
    - run_log 路径由 output.run_log 决定；JSONL 格式；可读最后 N 条判断「上次跑到哪一步」

**流程说明：** 执行数据处理前（用户说「跑数据处理」「执行流水线」）先完成 Step 1→2→3；确认后由 Agent 在后续步骤中调用 run_script 执行 phase 脚本（本流程仅负责配置确认，不发起 phase 执行）。仅改配置或查看时走 Step 4→5 或 Step 6。

**Error handling:**
- pipeline_config.json 不存在或 JSON 非法 → 提示放在本目录（skills/configuring-pipeline/）并检查语法
- 要改的键不在支持列表 → 见 references/natural-language-config-keys.md

---

# References

- **支持自然语言修改的键**：`references/natural-language-config-keys.md`
- **配置项说明与 run_log 用法**：项目根目录下 `pipeline_run_log_说明.md`
- **三个核心文件所在位置**：`references/where-are-the-three-files.md`
- **Skill 编写规范**：`guiding-skill-authoring/SKILL.md`

---

# Scripts（本目录内，由 data-pipeline-mcp 调用）

| 脚本 | 作用 | 调用示例 |
|------|------|----------|
| **scripts/show_pipeline_config.py** | 展示当前配置摘要（解析后的路径与 vectorizing.rebuild 等），供用户确认 | `run_script(script=scripts/show_pipeline_config.py, args=[])` |
| **scripts/apply_config_change.py** | 按键路径更新 pipeline_config.json 一项，供自然语言修改后落盘 | `run_script(script=scripts/apply_config_change.py, args=["base_dir", "data2"])` |

MCP 调用时 script 参数为 `scripts/show_pipeline_config.py` 或 `scripts/apply_config_change.py`，会在本目录的 scripts/ 下解析。

---

# 本目录内的三个共用文件

| 文件 | 作用 |
|------|------|
| **pipeline_config.json** | 唯一配置入口；与本 skill 的 loader 同目录，apply_config_change 写回此文件 |
| **pipeline_config_loader.py** | 加载并解析配置；各 phase 与本目录脚本将 skills/configuring-pipeline 加入 path 后 `load_config()` 使用 |
| **pipeline_run_logger.py** | 运行记录 JSONL 追加；各 phase 脚本在成功/失败时调用 `append_run_record(...)` |

**运行时环境（conda_env）：** 配置中的 `conda_env` 供用户在执行流水线前选择要使用的 conda 环境。执行 phase 脚本时，若 `conda_env` 非空，应在该环境中运行（例如 `conda run -n <conda_env> python <script>` 或先 `conda activate <conda_env>` 再执行）；空表示使用当前环境。

---

# Constraints

- **NEVER** execute phase scripts (e.g. phase0_sort_files.py) inside this flow — this flow is **config and confirm only**. Execution of phase scripts is done by the Agent in a separate step after user confirmation.
- **NEVER** change pipeline_config.json sensitive fields (e.g. api_key) to plain text without user consent; use "${env:VAR}" and remind the user to set the variable in the environment.
- This flow is **READ-ONLY** for device/data except for writing pipeline_config.json when the user explicitly requests a config change (apply_config_change.py or direct edit).
- 路径配置中 output.run_log 为文件路径（.jsonl），loader 会为其创建父目录而非把该路径当目录创建。
- Required output when showing config: base_dir, raw_material, key intermediate/output paths, and vectorizing.rebuild flags; when applying a change, confirm the key_path and value written.
