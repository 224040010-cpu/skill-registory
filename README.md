# Skill & Tool Registry：Agent 能力治理控制平面

> 仓库名 `skill-registory` 沿用现有 GitHub 地址。本仓库负责 Skill/Tool 的规划、规范、准入、版本、风险和发布，不承载 BPMN 编译、Graph 执行或真实 Agent 运行。

[![Governance CI](https://github.com/224040010-cpu/skill-registory/actions/workflows/skill-ci.yml/badge.svg?branch=master)](https://github.com/224040010-cpu/skill-registory/actions/workflows/skill-ci.yml)
[![Weekly Audit](https://github.com/224040010-cpu/skill-registory/actions/workflows/governance-cron.yml/badge.svg?branch=master)](https://github.com/224040010-cpu/skill-registory/actions/workflows/governance-cron.yml)
[![Platform Score](https://img.shields.io/badge/Platform%20Score-81%2F100-brightgreen)](reports/summary.json)
[![Governance](https://img.shields.io/badge/Governance-WARNING-yellow)](reports/summary.json)

## 一句话说明

`skill-registory` 是 Agent 系统的能力治理控制平面：它把零散的提示词、脚本和接口整理成可分类、可评审、可版本化、可审计、可被工作流安全引用的 Skill 与 Tool 资产。

## What：Skill、Tool 与治理体系是什么

### Skill 是什么

Skill 表达一个对用户或业务有独立价值的完整能力。它描述“在什么场景下，Agent 应如何完成一个目标”，通常包含业务判断、多个步骤、异常处理和结果质量要求。

一个可治理的 Skill 至少应说清：

- 触发场景和不适用场景；
- 输入、输出和完成证据；
- 执行步骤、分支和异常处理；
- 可调用的 Tool 及权限范围；
- Owner、版本、风险等级、评测和安全审查状态。

例如，“把业务需求转换为合规 BPMN”是 Skill，因为它需要理解意图、拆解步骤、处理分支、调用多个 Tool，并对最终流程负责。

### Tool 是什么

Tool 表达一个边界清晰、输入输出稳定的原子操作。它回答“Agent 可以调用哪个确定性能力”，而不是“如何完成整个业务目标”。

一个可治理的 Tool 至少应说清：

- 请求与响应 Schema；
- 服务和 Endpoint；
- 是否幂等；
- 是否产生副作用；
- 风险、审批和权限要求；
- 版本、Owner 以及被哪些 Skill 使用。

例如，“解析业务意图”“校验 BPMN XML 结构”是 Tool；它们可以被多个 Skill 复用，但自身不负责完整业务流程。

### Skill 与 Tool 如何区分

| 判断维度 | Skill | Tool |
|---|---|---|
| 核心语义 | 完成一个业务意图 | 执行一个原子操作 |
| 是否面向用户目标 | 是 | 通常否 |
| 是否包含业务判断或多步骤协作 | 可以 | 不应包含 |
| 接口稳定性 | 允许编排多个输入和阶段 | 应有稳定 Schema |
| 是否可被其他能力复用 | 可以 | 通常应当可以 |
| 治理重点 | 触发边界、效果、组合和评测 | 接口、副作用、幂等、权限和风险 |

如果一个步骤只服务某个父 Skill、没有独立复用和治理价值，它属于内部 `workflow_step`，不应为了“看起来模块化”而注册为 Skill 或 Tool。

### 治理体系是什么

治理不是把 `SKILL.md` 和 `TOOL.md` 收集到 Git 仓库，而是持续回答以下问题：

- 这个能力是否真的需要成为独立资产？
- 谁负责维护，它处于哪个版本和生命周期阶段？
- 它会访问什么数据、产生什么副作用、需要什么审批？
- 它依赖哪些 Skill/Tool，依赖是否仍然有效？
- 它是否通过结构校验、准入评审、安全审查和效果评测？
- 哪些资产允许被编译器发现，哪些必须继续隔离？

本仓库通过 Registry、状态机、双层 Gate、治理巡检和 Capability Catalog 把这些判断变成可执行规则。

### 核心治理产物

| 文件 | 作用 |
|---|---|
| [`skill-registry.yaml`](skill-registry.yaml) | Skill 的权威清单、版本、Owner、风险和生命周期 |
| [`tool-registry.yaml`](tool-registry.yaml) | Tool 的权威清单、接口属性、风险和消费关系 |
| [`catalog/catalog.snapshot.json`](catalog/catalog.snapshot.json) | 提供给 Workflow Factory 的不可变能力快照 |
| [`contracts/system-definition.json`](contracts/system-definition.json) | 双仓共享的系统总定义权威副本 |
| [`reports/summary.json`](reports/summary.json) | 治理健康度和待处理问题摘要 |

Catalog 不是 Registry 的简单复制。它只发布 `approved` 和 `restricted` 资产，并为每个资产附带版本、风险等级和 SHA-256 摘要。

## Why：为什么需要这套体系

当 Skill 和 Tool 只以文档、提示词或代码片段分散存在时，系统很快会出现以下问题：

- 相同能力被重复建设，名称相似但行为不一致；
- 流程步骤被过度包装成 Skill，造成路由冲突和能力爆炸；
- Tool 缺少 Schema、副作用和幂等说明，Agent 无法安全调用；
- 已废弃能力仍被新流程引用，运行结果随主分支变化而漂移；
- 高风险能力没有 Owner、审批和安全审查记录；
- 业务流程、能力资产和运行时全部堆在一个仓库，任何变更都扩大影响面。

因此，本项目把“能力是否可以用”和“流程如何执行”分开治理：Registry 负责资格与版本，Workflow Factory 负责组装与执行。这样可以获得确定性构建、最小权限、可审计变更和可重放运行。

## How：能力如何进入系统并被使用

### 资产准入流程

```text
Phase 0  能力规划：判断 Skill / Tool / 内部 workflow_step
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
Phase 1S  编写 Skill         Phase 1T  编写 Tool
           │                     │
Phase 2S  Skill 校验         Phase 2T  Tool 校验
           │                     │
Phase 3   以 draft/submitted 写入 Registry
           │                     │
Phase 4S  Skill 准入         Phase 4T  Tool 准入
           └──────────┬──────────┘
                      ▼
Phase 5   状态机检查、依赖检查和持续治理
                      ▼
Phase 6   发布 approved/restricted Capability Catalog
```

Authoring Gate 检查“是否写得完整、规范、可执行”；Admission Gate 检查“是否应该进入平台、是否冲突、风险是否可接受”。两个 Gate 都通过，仍不代表自动进入 Catalog，资产还必须具有允许发布的生命周期状态。

### 运行时消费流程

```text
Registry 发布固定 Catalog 快照
        ↓
Workflow Factory 解析所需 Skill/Tool
        ↓
生成 registry.lock.json，固定 Catalog、版本与摘要
        ↓
编译 BPMN、Workflow IR、Graph/Loop 和 Agent Profile
        ↓
签署 Registry Lock 与完整工作流软件包
        ↓
Runtime 验证信任链后执行、记录轨迹并支持重放
```

运行节点不得临时查询 Registry 主分支，也不得自动升级 Skill/Tool 版本。能力升级必须重新生成 Catalog、重新解析并重新签署软件包。

## Boundary：仓库职责边界

系统按控制平面和执行平面拆分：

| 范围 | `skill-registory` | `agent-workflow-factory` |
|---|---|---|
| 能力规划、Skill/Tool 规范 | 负责 | 消费 |
| Registry 生命周期和风险政策 | 负责 | 不负责 |
| Capability Catalog 发布 | 负责 | 固定并消费 |
| 自然语言转 BPMN | 不负责 | 负责 |
| BPMN 转 Workflow IR / Graph / Loop | 不负责 | 负责 |
| Agent Profile 和真实运行时 | 不负责 | 负责 |
| Registry Lock 与软件包签名 | 提供输入契约 | 负责 |
| 运行轨迹、暂停、恢复和重放 | 接收治理反馈 | 负责 |

两个仓库保存字节一致的 [`contracts/system-definition.json`](contracts/system-definition.json)。当前版本为 `3.0.0`，SHA-256 为 `f846e374ef89806a92c1adb45f387964842ff28c2fea142be4d86e7fef51f20c`。

完整职责契约、变更规则和故障隔离原则见 [`docs/repository-boundaries.md`](docs/repository-boundaries.md)。

## 当前治理状态

截至 2026-08-29：

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

`reports/summary.json` 当前为 `WARNING`，治理快照记录了 25 个历史复审过期项。2026-08-29 的本地全量门禁还识别出 4 个证券分析 draft Skill 引用了尚未注册的 `data-pipeline-mcp:run_script` 和 `file-system-mcp:list_files`。这些 Skill 保持 `draft` 并被 Catalog 隔离，不影响当前 35+15 个已发布资产。

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
