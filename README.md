# Skill & Tool Registry：Agent 能力治理控制平面

> 仓库名 `skill-registory` 沿用现有 GitHub 地址。本仓库负责 Skill/Tool 的规划、规范、准入、版本、风险和发布，不承载 BPMN 编译、Graph 执行或真实 Agent 运行。

[![Governance CI](https://github.com/224040010-cpu/skill-registory/actions/workflows/skill-ci.yml/badge.svg?branch=master)](https://github.com/224040010-cpu/skill-registory/actions/workflows/skill-ci.yml)
[![Weekly Audit](https://github.com/224040010-cpu/skill-registory/actions/workflows/governance-cron.yml/badge.svg?branch=master)](https://github.com/224040010-cpu/skill-registory/actions/workflows/governance-cron.yml)
[![Platform Score](https://img.shields.io/badge/Platform%20Score-81%2F100-brightgreen)](reports/summary.json)
[![Governance](https://img.shields.io/badge/Governance-WARNING-yellow)](reports/summary.json)

## 当前状态

截至 2026-08-29，仓库中的治理快照为：

| 指标 | 当前值 |
|---|---:|
| 注册 Skill | 43 |
| 注册 Tool | 15 |
| Catalog 可调用 Skill | 35 |
| Catalog 可调用 Tool | 15 |
| 被隔离的 draft Skill | 8 |
| 孤儿 Tool | 0 |
| 高风险调用链 | 0 |
| 平台治理分 | 81/100 |
| 当前本地全量门禁 | 19 通过，4 个 draft Skill 被拒绝 |

`reports/summary.json` 当前为 `WARNING`，治理快照记录了 25 个历史复审过期项。2026-08-29 的本地全量门禁还识别出 4 个证券分析 draft Skill 引用了尚未注册的 `data-pipeline-mcp:run_script` 和 `file-system-mcp:list_files`。这些 Skill 保持 `draft` 并被 Catalog 隔离，不影响当前 35+15 个已发布资产。只有 `approved` 和 `restricted` 状态会进入发布快照。

## 为什么拆成两个仓库

系统按“控制平面”和“执行平面”拆分：

```text
skill-registory（本仓库）
  业务能力规划 → Skill/Tool 编写 → 准入与风险治理
  → 发布 catalog/catalog.snapshot.json
                       │
                       ▼
agent-workflow-factory
  自然语言 → BPMN → Workflow IR → Graph/Loop
  → Agent Profile → DeepSeek Harness / Runtime
```

职责边界：

- 本仓库决定“哪些 Skill/Tool 可以被发现和使用”。
- [`agent-workflow-factory`](https://github.com/224040010-cpu/agent-workflow-factory) 决定“业务流程如何编译为可执行 Agent Graph”。
- 两个仓库保存字节一致的 [`contracts/system-definition.json`](contracts/system-definition.json)。当前版本为 `3.0.0`，SHA-256 为 `f846e374ef89806a92c1adb45f387964842ff28c2fea142be4d86e7fef51f20c`。
- Factory 编译时固定 Catalog 和资产摘要到 `registry.lock.json`；v0.9 进一步签署 Registry Lock 和完整工作流软件包。
- Runtime 只消费已固定的软件包，不在执行节点时读取 Registry 的 `master` 分支。

更完整的边界说明见 [`docs/repository-boundaries.md`](docs/repository-boundaries.md)。

## 核心产物

| 文件 | 用途 |
|---|---|
| [`skill-registry.yaml`](skill-registry.yaml) | Skill 权威注册表与生命周期状态 |
| [`tool-registry.yaml`](tool-registry.yaml) | Tool 权威注册表、风险和调用关系 |
| [`catalog/catalog.snapshot.json`](catalog/catalog.snapshot.json) | 提供给 Workflow Factory 的版本化能力目录 |
| [`contracts/system-definition.json`](contracts/system-definition.json) | 两仓共享的系统总定义权威副本 |
| [`reports/summary.json`](reports/summary.json) | 当前治理分数与健康状态摘要 |

Catalog 中每项资产都包含版本、状态、风险等级和 SHA-256 摘要。编译器只能解析 Catalog 中存在的资产。

## 治理流水线

```text
Phase 0   Capability Planning
          判断能力应该是 Skill、Tool，还是父 Skill 内部步骤
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
Phase 1S   Skill Authoring       Phase 1T   Tool Authoring
               │                     │
Phase 2S   Skill Validator       Phase 2T   Tool Validator
               │                     │
Phase 3    写入两类 Registry，并保持 draft/submitted 状态
               │                     │
Phase 4S   Skill Admission       Phase 4T   Tool Admission
               └──────────┬──────────┘
                          ▼
Phase 5    State Guard + Governance Audit
                          ▼
Phase 6    发布只含 approved/restricted 的 Capability Catalog
```

关键原则：

- 面向用户、包含业务判断和多步骤协作的完整意图，通常建模为 Skill。
- 单一、确定、可复用且有稳定输入输出 Schema 的原子操作，通常建模为 Tool。
- 只服务一个父流程、没有独立治理价值的步骤，不注册为全局资产。
- Tool 与 Skill 都必须经过 Authoring Gate 和 Admission Gate，避免 Skill explosion 变成 Tool explosion。

## 仓库结构

```text
skill-registory/
├── capability-planning/          # Phase 0：能力分类与拆分
├── guiding-skill-authoring/      # Skill 编写规范和校验器
├── guiding-tool-authoring/       # Tool 编写规范和校验器
├── skill-admission-review/       # Skill 准入门禁
├── tool-admission-review/        # Tool 准入门禁
├── skill-governance-agent/       # 持续治理与审计
├── business-to-bpmn/             # BPMN 领域 Skill/Tool 资产
├── stock-analysis-skills/        # 金融/证券分析领域资产
├── catalog/                      # 可供编译器消费的发布快照
├── contracts/                    # 双仓共享总定义
├── scripts/                      # 状态检查、CI、Catalog 和报告工具
├── reports/                      # 治理报告
├── skill-registry.yaml
└── tool-registry.yaml
```

## 快速开始

### 1. 准备环境

Windows PowerShell、WSL 或 Linux 均可：

```bash
git clone https://github.com/224040010-cpu/skill-registory.git
cd skill-registory
python -m pip install pyyaml
```

建议使用 Python 3.10 或更高版本。

### 2. 检查共享总定义

```bash
python scripts/verify_system_definition.py
```

若两个仓库位于同一机器，可同时检查 Factory 镜像是否逐字节一致：

```bash
python scripts/verify_system_definition.py \
  --peer ../agent-workflow-factory/contracts/system-definition.json
```

### 3. 运行状态与治理检查

```bash
python scripts/state_guard.py
python scripts/ci_runner.py --all
```

`state_guard.py` 检查生命周期、风险和依赖关系；`ci_runner.py` 对实际存在的 Skill/Tool 同时运行编写校验和准入门禁。

当前基线中，`state_guard.py` 应返回 `PASS`；`ci_runner.py --all` 会以非零状态列出 4 个仍处于 `draft` 的证券分析 Skill，因为它们依赖的两个 MCP Tool 尚未注册。应先补齐 Tool 契约并通过 Tool Admission，再提升这些 Skill 的状态。

### 4. 重新生成 Catalog

```bash
python scripts/publish_catalog.py
```

生成结果位于 `catalog/catalog.snapshot.json`。提交前应检查快照差异，确认没有意外资产进入或退出运行时可见范围。

## 新增或变更资产

### 新增 Skill

1. 使用 [`capability-planning/SKILL.md`](capability-planning/SKILL.md) 完成能力分类。
2. 按 [`guiding-skill-authoring/SKILL.md`](guiding-skill-authoring/SKILL.md) 创建 `SKILL.md`。
3. 在 `skill-registry.yaml` 中以 `draft` 状态登记。
4. 运行编写校验和准入门禁：

```bash
python guiding-skill-authoring/scripts/validate_skill.py <目录>/SKILL.md
python skill-admission-review/scripts/admission_gate.py \
  <目录>/SKILL.md --registry skill-registry.yaml
```

### 新增 Tool

1. 确认它是有稳定 Schema 的原子能力，而不是业务流程。
2. 按 [`guiding-tool-authoring/SKILL.md`](guiding-tool-authoring/SKILL.md) 创建 `TOOL.md`。
3. 在 `tool-registry.yaml` 中以 `draft` 状态登记。
4. 运行编写校验和准入门禁：

```bash
python guiding-tool-authoring/scripts/validate_tool.py <目录>/TOOL.md
python tool-admission-review/scripts/admission_gate_tool.py \
  <目录>/TOOL.md --registry tool-registry.yaml
```

## 生命周期与发布规则

```text
draft → submitted → approved | restricted | needs_revision
needs_revision → submitted
approved ↔ restricted
approved | restricted → deprecated → retired
```

| 状态 | 进入 Catalog | Factory 行为 |
|---|---|---|
| `approved` | 是 | 可解析并写入 Registry Lock |
| `restricted` | 是 | 可解析，但必须满足额外策略 |
| `draft` | 否 | 不可见 |
| `submitted` | 否 | 不可见 |
| `needs_revision` | 否 | 不可见 |
| `deprecated` | 否 | 新编译不得引用 |
| `retired` | 否 | 必须拒绝 |

资产版本、状态、风险级别或内容发生变化后，应重新发布 Catalog。已编译软件包不会自动漂移到新版本，必须显式重新解析并生成新的 `registry.lock.json`。

## CI 与自动治理

仓库包含以下 GitHub Actions：

| Workflow | 作用 |
|---|---|
| `skill-ci.yml` | Registry、Skill、Tool 和 Catalog 的主检查链 |
| `incoming-precheck.yml` | 新 Bundle 进入主仓库前预检 |
| `admission-gate.yml` | 准入门禁 |
| `governance-cron.yml` | 周期治理审计 |
| `post-merge.yml` | 合并后的报告和 Catalog 刷新 |

常用本地命令：

```bash
# 检查状态机
python scripts/state_guard.py

# 检查全部本地资产
python scripts/ci_runner.py --all

# 发布能力目录
python scripts/publish_catalog.py

# 生成治理报告
python scripts/generate_reports.py
```

## 与 Workflow Factory 联调

推荐采用固定快照，而不是让 Factory 直接读取 Registry 主分支：

1. Registry 完成准入并发布 `catalog/catalog.snapshot.json`。
2. Factory 复制或下载该快照作为一次构建输入。
3. Factory 解析所需 Skill/Tool，生成包含 Catalog 摘要和资产摘要的 `registry.lock.json`。
4. Factory v0.9 使用构建密钥签署 Registry Lock 与完整软件包 Manifest。
5. DeepSeek Harness 运行前验证离线根信任、Binding 清单、Registry Lock 和软件包 Manifest。

这样即使 Registry 暂时不可用或后续发生变化，已经签署的软件包仍可确定性执行和重放。

## 当前治理注意事项

- 目前有 8 个 `draft` Skill，不会进入 Catalog。
- 其中 4 个证券分析 Skill 的全量门禁会被拒绝，原因是引用了尚未注册的 `data-pipeline-mcp:run_script` 和 `file-system-mcp:list_files`；这是有效阻断，不应跳过。
- 治理报告标记了 25 个历史复审过期项，应逐项更新 `last_reviewed`，而不是批量修改日期掩盖真实审查状态。
- Catalog 的 `source_present` 字段会标识资产源文件是否位于本仓库；缺失源文件的历史资产应逐步迁移或明确外部来源。
- 本仓库发布 Catalog，但不持有生产构建私钥、根私钥或 DeepSeek API Key。
- 共享总定义变更需要提升 `definition_version`、刷新校验和，并同步更新两个仓库；普通 Skill/Tool 变更不应修改总定义。

## 进一步阅读

- [仓库职责边界](docs/repository-boundaries.md)
- [银行/金融行业迁移指南](docs/banking-migration-guide.md)
- [银行领域治理补充规范](docs/banking-supplement.md)
- [Capability Catalog 说明](catalog/README.md)
- [Agent Workflow Factory v0.9](https://github.com/224040010-cpu/agent-workflow-factory/blob/main/docs/deepseek-readonly-v0.9.md)

---

README 更新于 2026-08-29，反映双仓拆分、Capability Catalog 发布以及 Agent Workflow Factory v0.9 信任链的当前状态。
