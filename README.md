# Skill & Tool Registry — 双轨能力治理体系

> **能力从"业务需求"到"可稳定调用的平台资产"的完整规划、生成、校验与治理机制**

---

## 目录

- [体系概览](#体系概览)
- [仓库结构](#仓库结构)
- [七阶段详解](#七阶段详解)
  - [Phase 0 能力规划](#phase-0--能力规划capability-planning)
  - [Phase 1S Skill 生成](#phase-1s--skill-生成)
  - [Phase 1T Tool 生成](#phase-1t--tool-生成)
  - [Phase 2 本地校验](#phase-2--本地校验authoring-gate)
  - [Phase 3 Registry 注册](#phase-3--registry-注册)
  - [Phase 4 准入门禁](#phase-4--准入门禁admission-gate)
  - [Phase 4T Tool 准入门禁](#phase-4t--tool-准入门禁)
  - [Phase 5 持续治理](#phase-5--持续治理)
- [资产升降级规则](#资产升降级规则)
- [两类资产的本质区别](#两类资产的本质区别)
- [两类 Gate 的本质区别](#两类-gate-的本质区别)
- [工作流操作手册](#工作流操作手册)
  - [提交者：上传新 Bundle](#提交者上传新-bundle)
  - [管理员：运行准入流程](#管理员运行准入流程)
  - [管理员：日常治理巡检](#管理员日常治理巡检)
- [Skill 状态机](#skill-状态机)
- [工具速查](#工具速查)
- [Phase 6 · CI / Runtime Integration](#phase-6--ci--runtime-integration)
- [已知限制与计划改进](#已知限制与计划改进)

---

## 体系概览

```
                    ┌─────────────────────┐
                    │   Phase 0           │
                    │ capability-planning │
                    │ (decompose+classify) │
                    │ → capability_plan   │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼───────────────┐
               ↓ type=skill                    ↓ type=tool
   ┌───────────────────────┐       ┌────────────────────────┐
   │  Phase 1S             │       │  Phase 1T              │
   │ guiding-skill-        │       │ guiding-tool-          │
   │ authoring             │       │ authoring              │
   │ → SKILL.md            │       │ → TOOL.md              │
   └──────────┬────────────┘       └───────────┬────────────┘
              │                                │
   ┌──────────▼────────────┐       ┌───────────▼────────────┐
   │  Phase 2S             │       │  Phase 2T              │
   │ validate_skill.py     │       │ validate_tool.py       │
   │ (7维度 / 70分)         │       │ (5维度 / 50分)          │
   └──────────┬────────────┘       └───────────┬────────────┘
              │                                │
   ┌──────────▼────────────┐       ┌───────────▼────────────┐
   │  Phase 3              │       │  Phase 3T              │
   │ skill-registry.yaml   │       │ tool-registry.yaml     │
   │ (status: draft)       │       │ + mcp-tool-catalog     │
   └──────────┬────────────┘       └────────────────────────┘
              │
   ┌──────────▼────────────┐
   │  Phase 4              │
   │ admission_gate.py     │
   │ (5项准入检查)           │
   └──────────┬────────────┘
              │
   ┌──────────▼────────────┐       (Tool path)
   │  Phase 4T             │       ┌────────────────────────┐
   │ admission_gate_tool   │       │  tool-registry.yaml    │
   │ .py (5项Tool准入检查)   │──────►│  status: approved      │
   └──────────┬────────────┘       └────────────────────────┘
              │
   ┌──────────▼────────────┐
   │  Phase 5              │
   │ governance_audit.py   │
   │ (4类持续巡检)           │
   └───────────────────────┘
```

**五个核心问题**

| 问题 | 解决阶段 |
|------|---------|
| 一个业务需求被过度拆分成大量碎片化 Skill | **Phase 0** |
| 什么该是 Skill，什么该是 Tool，什么是 Skill 内部编排步骤 | **Phase 0** |
| Skill 写出来但结构不完整、边界不清、描述不可路由 | Phase 1S + Phase 2S |
| Tool 没有明确接口定义、风险未声明、无法被工程实现 | Phase 1T + Phase 2T |
| Skill/Tool 进入仓库后会漂移、重复、过期、失效 | Phase 4 + Phase 5 |

---

## 仓库结构

```
skill-registry/
│
├── skill-registry.yaml              # Skill 中央注册表（30 个 Skill）
├── tool-registry.yaml               # Tool 中央注册表（15 个 Tool）✦ NEW
├── skill-intake.ps1                 # 管理员准入工作流脚本
│
├── capability-planning/             # Phase 0: 能力规划 meta-skill
│   ├── SKILL.md
│   ├── evals/evals.json
│   └── references/
│       ├── classification-guide.md  # skill/tool/workflow_step 判定示例
│       ├── anti-patterns.md         # 6类常见碎片化反模式
│       └── asset-promotion-rules.md # 升降级正式规则 ✦ NEW
│
├── guiding-skill-authoring/         # Phase 1S: Skill 生成指导 meta-skill
│   ├── SKILL.md
│   ├── scripts/
│   │   └── validate_skill.py        # Phase 2S: 7维度评分校验器
│   └── references/
│       ├── validation-rubric.md
│       ├── mcp-tool-catalog.md      # 注册 MCP 服务端（含 bpmn-tools）
│       ├── naming-guide.md
│       └── platform-constraints.md
│
├── guiding-tool-authoring/          # Phase 1T: Tool 生成指导 meta-skill ✦ NEW
│   ├── SKILL.md
│   ├── scripts/
│   │   └── validate_tool.py         # Phase 2T: 5维度工具规格校验器
│   ├── assets/
│   │   └── tool-template.md         # TOOL.md 可填写模板
│   └── references/
│       └── tool-governance.md       # 风险矩阵、命名规范、Admission规则
│
├── tool-admission-review/           # Phase 4T: Tool 准入门禁 meta-skill ✦ NEW
│   ├── SKILL.md
│   ├── scripts/
│   │   └── admission_gate_tool.py   # 5项Tool准入检查
│   └── references/
│       └── tool-admission-policy.md
│
├── skill-admission-review/          # Phase 4: 准入门禁 meta-skill
│   ├── SKILL.md
│   ├── scripts/
│   │   └── admission_gate.py        # 5项准入检查
│   └── references/
│       └── admission-policy.md
│
├── skill-governance-agent/          # Phase 5: 持续治理 meta-skill
│   ├── SKILL.md
│   ├── scripts/
│   │   └── governance_audit.py      # 4类巡检 + 双报告输出
│   └── references/
│       └── governance-policy.md
│
├── scripts/                         # 批量工具
│   ├── batch_admission.py
│   ├── batch_fix_frontmatter.py
│   └── fix_risk_levels.py
│
├── reports/                         # 自动生成的报告
│   ├── admission_<bundle>.txt
│   ├── governance_report_YYYYMMDD.json
│   └── manual_review_queue.json
│
├── ev-charger-skills/               # 已入库 Bundle（24 个 Skill）
└── business-to-bpmn/                # 已入库 Bundle（3 个 Skill + 15 个 Tool）✦ 重构
    ├── SKILL.md                     # converting-business-to-bpmn（主编排 Skill）
    ├── decomposing-business-process/SKILL.md  # 可独立触发的流程规划 Skill
    ├── validating-bpmn-compliance/SKILL.md    # 可独立触发的 BPMN 校验 Skill
    ├── capability_plan.json         # 重构依据（能力规划产出物）
    ├── tools/
    │   ├── tool-catalog.md          # 15 个工具规格文档
    │   ├── parse-business-intent/TOOL.md
    │   └── validate-bpmn-structural/TOOL.md
    └── references/
```

**Git 分支结构**

```
master                          ← 平台基础设施 + 已入库资产
incoming/<bundle>               ← 提交者专用，仅含 bundle 目录（orphan branch）
```

---

## 七阶段详解

### Phase 0 · 能力规划（Capability Planning）

**目标**：在生成任何 Skill 或 Tool 之前，先将业务需求拆解为原子能力单元，判定每个单元的形态，防止碎片化和架构污染。

**执行者**：`capability-planning/SKILL.md`（meta-skill）

**判定决策树**

```
Q1 是否是单一、确定性的原子操作？（与触发方无关）
├── 是 → TOOL ──► Phase 1T（guiding-tool-authoring）
└── 否 → Q2

Q2 是否代表一个完整用户意图，值得独立治理/注册/路由/测试？
├── 是 → SKILL ──► Phase 1S（guiding-skill-authoring）
└── 否 → workflow_step  ← 不是第三种能力类型
                         嵌入父 Skill 的 composition_notes
                         不进 registry，不参与全局路由
```

**Self-Critique 五项防碎片化检查**

| 检查 | 触发条件 | 动作 |
|------|---------|------|
| A — Tool 伪装成 Skill | skill 只有 ≤1 步且无错误处理 | 降级为 tool |
| B — 过度拆分 | 两个 skill 描述重叠 >70% | 合并 |
| C — 触发依赖 | skill 只能由另一 skill 触发 | 嵌入父 Skill 的 composition_notes（非第三类型） |
| D — Agent 边界越界 | skill 涉及多个 bundle_scope | 按 agent 拆分 |
| E — 数量爆炸 | skill 总数 >7 | 重新审视分类 |

**产出**：`capability_plan.json`

```json
{
  "schema_version": "1.1",
  "summary": { "skills": 2, "tools": 5, "workflow_steps_embedded": 3 },
  "capabilities": [
    { "id": "cap-01", "final_type": "skill", "name": "converting-business-to-bpmn" },
    { "id": "cap-04", "final_type": "tool",  "name": "parse-business-intent" }
  ],
  "composition_notes": [
    { "step_id": "step-01", "name": "normalise-alarm-codes",
      "belongs_to_skill": "cap-01", "placement": "after cap-04" }
  ],
  "next_actions": [
    { "capability_id": "cap-01", "action": "Start guiding-skill-authoring" },
    { "capability_id": "cap-04", "action": "Start guiding-tool-authoring" }
  ]
}
```

**真实案例**：`business-to-bpmn` bundle 经 Phase 0 规划后，从 16 个"Skill"重构为 **3 个真正的 Skill + 13 个 MCP Tool**，消除了 13 个流水线步骤被错误注册为 Skill 的问题。

> **这一层回答**："要写几个 Skill，几个 Tool，哪些根本不该是任何资产"

---

### Phase 1S · Skill 生成

**目标**：把一个已确认为 skill 类型的能力，转成结构化 SKILL.md 草稿

**执行者**：`guiding-skill-authoring/SKILL.md`（meta-skill）

**8 问意图采集**

1. 这个 Skill 解决什么业务问题？
2. 触发场景是什么？（用户说什么时调用）
3. 不触发场景是什么？
4. 所属 Agent 是哪个？（`bundle_scope`）
5. 是否需要设备控制？（影响 `risk_level`）
6. 是否有语音播报要求？（影响 TTS 约束）
7. 需要哪些输入参数？
8. 输出什么？

**产出**：`SKILL.md`（含 frontmatter + Purpose / Trigger / Workflow / Constraints 四节）

> **这一层只回答**："这个 Skill 能不能被写出来、怎么写出来"

---

### Phase 1T · Tool 生成

**目标**：把一个已确认为 tool 类型的能力，转成完整的 TOOL.md 规格文档

**执行者**：`guiding-tool-authoring/SKILL.md`（meta-skill）

**前置拒绝测试**（任一命中则拒绝进入此阶段）

```
[ ] 能力需要多步推理或条件分支          → SKILL，不是 Tool
[ ] 能力有自然语言用户触发              → SKILL，不是 Tool
[ ] 能力编排其他工具或 Skill            → SKILL 或 Workflow
[ ] 能力输出依赖跨轮对话上下文          → SKILL，不是 Tool
```

**Tool 风险等级**

| Level | side_effects | 典型场景 |
|---|---|---|
| L0 | none | 纯计算：序列化、格式转换、图算法 |
| L1 | read | 读数据库、索引检索、状态查询 |
| L2 | read | LLM 推理、复杂分析（非确定性） |
| L3 | write | 创建/更新记录、发送通知 |
| L4 | external | 设备命令、支付、OTA 推送 |

**产出**：`TOOL.md`（纯 YAML 接口规格，含 input_schema / output_schema / errors / risk / usage）

```yaml
tool_name: parse-business-intent
category: parsing
risk:
  level: L1
  side_effects: read
  idempotent: true
input_schema:
  type: object
  required: [user_description]
  properties:
    user_description: { type: string, description: "..." }
output_schema:
  type: object
  properties:
    business_type: { type: string, ... }
    goal: { type: string, ... }
errors:
  - code: INVALID_INPUT
    message: "..."
    retryable: false
  - code: EXECUTION_FAILED
    message: "..."
    retryable: true
```

> **这一层回答**："这个 Tool 的接口是什么、风险是什么、谁来实现"

---

### Phase 2 · 本地校验（Authoring Gate）

#### Phase 2S — Skill 校验

**执行者**：`guiding-skill-authoring/scripts/validate_skill.py`

**7 个评分维度（满分 70）**

| # | 维度 | 满分 | 核心检查项 |
|---|------|------|-----------|
| 1 | Trigger Clarity | 10 | 第三人称、`Use when`、`Do NOT use when`、模糊词惩罚 |
| 2 | Workflow Executability | 10 | `[ ] Step N:` 格式、`server:tool_name()` 调用、异常分支 |
| 3 | MCP Tool Compliance | 10 | 工具引用注册验证（对照 mcp-tool-catalog.md）、L4 需 Verify Gate |
| 4 | Input/Output Contract | 10 | 明确输入参数、输出定义、TTS 约束（若 voice 平台） |
| 5 | Constraints & Safety | 10 | `# Constraints` 节、NEVER 声明、作用域声明、必填输出字段 |
| 6 | Single Responsibility | 10 | 无连词过载、无跨 Skill 调用、无混合输出类型 |
| 7 | Testability | 10 | 输入输出示例、边界案例、`evals/evals.json` |

**判定标准**（统一词汇）

| 分数 | 结果码 | 含义 |
|------|--------|------|
| ≥ 60，无 blocking_issues | `PASS` | 可直接提交 |
| ≥ 45 | `PASS_WITH_WARNINGS` | 有小修改，带 review 可提交 |
| 30–44 | `REQUIRES_REVIEW` | 需较大修改，不可直接提交 |
| < 30 | `REJECT` | 需重写 |

```bash
python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md
python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md --json
```

#### Phase 2T — Tool 校验

**执行者**：`guiding-tool-authoring/scripts/validate_tool.py`

**5 个评分维度（满分 50）**

| # | 维度 | 满分 | 核心检查项 |
|---|------|------|-----------|
| 1 | Naming & Description | 10 | kebab-case + verb-noun 命名、描述非模糊、≤120字符 |
| 2 | Schema Integrity | 10 | 所有 input/output 字段有 type + description、无 `type: any` |
| 3 | Risk & Safety | 10 | risk_level 与 side_effects 一致性（矩阵校验）、L3/L4 需 requires_approval |
| 4 | Error Contract | 10 | ≥2 错误码、UPPER_SNAKE_CASE、retryable 标注、含 input + system 两类错误 |
| 5 | Atomicity & Reusability | 10 | 非流程编排、implementation.endpoint 已声明、called_by_skills 非空 |

**判定标准**（统一词汇）

| 分数 | 结果码 | 含义 |
|------|--------|------|
| ≥ 45 | `PASS` | 可直接提交 |
| 40–44 | `PASS_WITH_WARNINGS` | 有小修改，带 review 可提交 |
| 30–39 | `REQUIRES_REVIEW` | 需较大修改 |
| < 30 | `REJECT` | 需重写 |

```bash
python guiding-tool-authoring/scripts/validate_tool.py <tool>/TOOL.md
python guiding-tool-authoring/scripts/validate_tool.py <tool>/TOOL.md --json
```

---

### Phase 3 · Registry 注册

#### Skill Registry（skill-registry.yaml）

```yaml
- skill_name: converting-business-to-bpmn
  display_name: Converting Business to BPMN
  purpose: "一句话描述，用于路由匹配"
  owner_team: bpmn
  version: "2.0.0"
  status: draft           # 初始状态
  risk_level: L2
  bundle_scope: bpmn-agent
  supported_models: [claude-sonnet-4-6]
  eval_status: pending
  path: business-to-bpmn/SKILL.md
  created_at: "2026-03-17"
  last_reviewed: "2026-03-17"
```

Skill 状态生命周期：`draft → submitted → approved → deprecated → retired`

#### Tool Registry（tool-registry.yaml）

```yaml
- tool_name: parse-business-intent
  category: parsing
  risk_level: L1
  side_effects: read
  idempotent: true
  owner_team: bpmn
  service: bpmn-tools        # MCP 服务名
  status: approved
  path: business-to-bpmn/tools/parse-business-intent/TOOL.md
  called_by_skills:
    - converting-business-to-bpmn
    - decomposing-business-process
```

Tool 状态生命周期：`draft → submitted → approved → deprecated → retired`

**注册时机**：通过 Authoring Gate 后以 `draft` 状态先入 Registry，再走 Admission Gate。

> **这一层是资产登记，不是上线批准。**

---

### Phase 4 · 准入门禁（Admission Gate）

**目标**：从平台视角判断"这个 Skill 该不该正式进入平台"（仅适用于 Skill）

**执行者**：`skill-admission-review/scripts/admission_gate.py`

**5 项检查**

| # | 检查项 | 关键判定 |
|---|--------|---------|
| 1 | **全局冲突检查** | 同名 → REJECT；编辑距离 ≤2 → WARNING；Jaccard 相似度 >0.65 → REQUIRES_REVIEW |
| 2 | **Agent 边界检查** | `bundle_scope` 缺失/无效 → REJECT；跨 Agent 词汇污染 → REQUIRES_REVIEW |
| 3 | **风险等级检查** | 设备控制词但非 L4 → REJECT；L1 含写操作词 → REQUIRES_REVIEW |
| 4 | **路由治理检查** | 描述过短/无触发子句/含模糊词 → WARNING；描述过宽泛 → REQUIRES_REVIEW |
| 5 | **形态合理性检查** | 调用其他 Skill → REJECT；步骤过少无异常处理 → WARNING |

**4 种准入决策**

| 决策 | 含义 | 操作 |
|------|------|------|
| `PASS` | 可正式进入 Registry | 更新 `status: approved` |
| `PASS_WITH_WARNINGS` | 可进入，有治理提醒 | 更新为 `approved / restricted` |
| `REQUIRES_REVIEW` | 需人工审核 | 更新为 `needs_revision` |
| `REJECT` | 不适合准入 | 保持 `draft`，返回修改意见 |

```bash
python skill-admission-review/scripts/admission_gate.py <skill>/SKILL.md --registry skill-registry.yaml
python scripts/batch_admission.py ev-charger-skills business-to-bpmn
```

> **这一层是平台治理门**：检查 Skill 该不该进，不管 Skill 写得对不对。

---

---

### Phase 4T · Tool 准入门禁

**目标**：从平台视角判断"这个 Tool 该不该正式进入 tool-registry.yaml"

> 与 Phase 4（Skill 准入）并列，补全双轨治理的最后一块缺口。
> validate_tool.py 已回答"写得好不好"；Phase 4T 回答"该不该进"。

**执行者**：`tool-admission-review/scripts/admission_gate_tool.py`

**5 项检查**

| # | 检查项 | 关键判定 |
|---|--------|---------|
| 1 | **全局重复检查** | 同名/近名 → REJECT；描述 Jaccard ≥ 65% → REQUIRES_REVIEW；schema 字段重叠 ≥ 70% → REQUIRES_REVIEW |
| 2 | **服务归属检查** | `service` 缺失 → REJECT；新服务仅 1 个 Tool → WARNING；功能近似但服务不同 → REQUIRES_REVIEW |
| 3 | **风险一致性检查** | L0+side_effects≠none → REJECT；L4+requires_approval≠true → REJECT；L3 无 approval → WARNING |
| 4 | **复用合理性检查** | called_by_skills 为空 → REJECT；仅 1 个 skill 使用 → WARNING；≥ 2 个 skill → PASS |
| 5 | **形态合理性检查** | 名称含 manager/handler/orchestrator → REJECT；描述含编排语言 → REQUIRES_REVIEW；描述 > 250 字符 → WARNING |

**4 种准入决策**

| 决策 | 含义 | 操作 |
|------|------|------|
| `PASS` | 可正式进入 Registry | 更新 `status: approved` |
| `PASS_WITH_WARNINGS` | 可进入，有治理提醒 | 更新为 `approved`，记录 warning |
| `REQUIRES_REVIEW` | 需人工审核 | 保持 `draft`，等待 reviewer |
| `REJECT` | 不适合准入 | 返回修改意见，可能降级为 workflow_step |

```bash
python tool-admission-review/scripts/admission_gate_tool.py \
  <tool>/TOOL.md \
  --registry tool-registry.yaml

python tool-admission-review/scripts/admission_gate_tool.py \
  <tool>/TOOL.md \
  --registry tool-registry.yaml \
  --json
```

> **Check 4 是唯一无条件 REJECT**：零消费者的 Tool 直接拒绝，不论其他检查是否通过。


### Phase 5 · 持续治理（双轨）

**目标**：让治理从一次性准入变成持续过程，覆盖 Skill 和 Tool 两轨以及跨轨一致性

**执行者**：`skill-governance-agent/scripts/governance_audit.py`

**10 项巡检（三组）**

| 组 | 检查 | 检查内容 | 严重级别 |
|----|------|---------|---------|
| Skill | S1 仓库一致性 | 仓库有而 Registry 无；name 字段漂移 | HIGH / WARNING |
| Skill | S2 元数据健康 | 必填字段缺失；purpose 过短/模糊；命名不规范 | HIGH / WARNING |
| Skill | S3 冲突漂移 | 已上线 Skill 间 purpose 相似度监控；family_overload | HIGH / WARNING |
| Skill | S4 生命周期 | 审查超期（180天）；L4 安全审查逾期（30天）→ CRITICAL | CRITICAL / HIGH |
| Tool | T1 Tool 仓库一致性 | tool-registry 有而无 TOOL.md；name 字段漂移 | HIGH / WARNING |
| Tool | T2 Tool 元数据健康 | 必填字段；category/risk_level/side_effects 一致性 | HIGH / WARNING |
| Tool | T3 Tool 生命周期 | 审查超期；L3/L4 工具 60 天高频巡检 | CRITICAL / HIGH |
| Tool | T4 消费者完整性 | 零消费者 → HIGH；单消费者 → WARNING；引用失效 skill | HIGH / WARNING |
| Cross | X1 死亡工具引用 | Skill 调用不存在于 tool-registry 的工具 | HIGH |
| Cross | X2 废弃工具使用 | Skill 调用已 deprecated/retired 的工具 | HIGH |
| Cross | X3 风险继承缺口 | 调用 L4 Tool 的 Skill 自身 risk_level < L4 | HIGH |

```bash
# 完整双轨巡检
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --tool-registry tool-registry.yaml \
  --skills-root . \
  --output reports/ \
  --update-timestamp

# 仅 Skill（向后兼容）
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  --skills-only
```

生成：`reports/governance_report_YYYYMMDD.json` + `reports/manual_review_queue.json`

报告结构新增 `by_asset_type`：`{ skill: N, tool: N, cross: N }`

---

## 两类资产的本质区别

```
                  SKILL                         TOOL                      workflow_step
                  ─────────────────────         ──────────────────────    ─────────────────────
层次               能力层                        能力层                    编排实现层
触发方式           用户自然语言意图              Skill 代码中的程序调用    无独立触发
步骤数量           多步骤（有条件分支）           单步原子操作              单步，附属于父 Skill
规格文件           SKILL.md（YAML + Markdown）   TOOL.md（纯 YAML）        无独立规格文件
校验工具           validate_skill.py（70分）     validate_tool.py（50分）  随父 Skill 测试
注册位置           skill-registry.yaml           tool-registry.yaml        composition_notes 字段
调用格式           由 Agent Router 路由           server:tool_name()        父 Skill Workflow 内调用
可被路由           是                            否（只能被 Skill 调用）   否（不参与全局路由）
```

> `workflow_step` 可升级为 `skill`（满足独立复用/治理条件）或降级为 `tool`（发现本质原子）。

**一个业务功能的正常形态**：

```
用户请求
  ↓ 路由
SKILL（多步推理）
  ↓ 调用
TOOL-1 → TOOL-2 → TOOL-3（原子操作）
  ↓
输出
```

---

## Phase 6 · CI / Runtime Integration

> **目标：不依赖人记得去做，而是系统自动拦。**

### 三项核心机制

| 机制 | 脚本 / 文件 | 作用 |
|------|------------|------|
| **PR 级自动检查** | `.github/workflows/skill-ci.yml` | 每次 push/PR 自动运行 State Guard + Validate + Admission |
| **状态机强制执行** | `scripts/state_guard.py` | 拦截违反生命周期规则的 registry 变更 |
| **Runtime 只消费 approved 资产** | `scripts/runtime_allowlist.py` | 生成 `runtime/allowlist.json`，Runtime 必须基于此文件路由 |

---

### Phase 6-A · PR 级自动检查（GitHub Actions）

**文件：** `.github/workflows/skill-ci.yml`

每次 push 或 PR 触发（paths: `**/SKILL.md`, `**/TOOL.md`, `skill-registry.yaml`, `tool-registry.yaml`）：

```
Stage 1  State Guard
         python scripts/state_guard.py
         → 违反状态机规则 → CI 立即失败

Stage 2  Validate + Admission Gate (仅变更的文件)
         SKILL.md → validate_skill.py + admission_gate.py
         TOOL.md  → validate_tool.py  + admission_gate_tool.py
         → 任意 REJECT → CI 失败
         → REQUIRES_REVIEW → CI 失败
         → PASS_WITH_WARNINGS → CI 通过，报告中标记

Stage 3  Runtime Allowlist 再生
         python scripts/runtime_allowlist.py
         → 上传 runtime/allowlist.json 为 build artifact
```

**CI 触发方式（workflow_dispatch 支持全量检查）：**

```bash
# 仅检查变更文件（默认 PR/push 行为）
git push origin feature/my-new-skill

# 手动触发全量检查
# GitHub Actions → workflow_dispatch → check_all: true
```

---

### Phase 6-B · 状态机强制执行（State Guard）

**文件：** `scripts/state_guard.py`

**状态机规则（skill 和 tool 共用）：**

```
draft → submitted → approved | restricted | needs_revision
needs_revision → submitted
approved ↔ restricted
approved | restricted → deprecated → retired
```

**检查规则：**

| 规则 ID | 级别 | 描述 |
|---------|------|------|
| S-STATE-1 | CRITICAL | 无效 status 值 |
| S-STATE-2 | HIGH | L4 skill 未通过 security_review |
| S-STATE-3 | CRITICAL | approved skill 依赖 draft/submitted/needs_revision skill |
| S-STATE-4 | CRITICAL/HIGH | approved skill 依赖 retired/deprecated skill |
| S-STATE-5 | HIGH | 依赖的 skill 不存在于 registry |
| T-STATE-1 | CRITICAL | Tool 无效 status 值 |
| T-STATE-2 | WARNING | approved tool 的 consumer skill 已 retired |
| T-STATE-3 | WARNING | approved tool 的 consumer skill 不在 registry |
| T-STATE-4 | CRITICAL/HIGH | deprecated/retired tool 仍被 active skill 调用 |

**使用方式：**

```bash
# 人类可读输出
python scripts/state_guard.py

# JSON 报告（CI 用）
python scripts/state_guard.py --output reports/ci/state-guard.json

# 仅 JSON 输出到 stdout
python scripts/state_guard.py --json
```

**Exit codes:** `0` = PASS，`1` = FAIL（有 CRITICAL/HIGH），`3` = WARN（仅 WARNING），`2` = 解析错误

---

### Phase 6-C · Runtime 只消费 approved 资产

**文件：** `scripts/runtime_allowlist.py` → `runtime/allowlist.json`

这是 Registry 与 Runtime 之间的**合同**：

> Runtime MUST NOT call any skill or tool not present in `allowlist.json`.

**哪些资产进入 allowlist：**

| Status | 进入 allowlist | Runtime 行为 |
|--------|--------------|-------------|
| `approved` | **是** | 可正常调用 |
| `restricted` | **是** | 需额外权限校验 |
| `draft` | 否 | Runtime 不可见 |
| `submitted` | 否 | Runtime 不可见 |
| `needs_revision` | 否 | Runtime 不可见 |
| `deprecated` | 否 | Runtime 拒绝并记录告警 |
| `retired` | 否 | Runtime 强制报错 |

**生成方式：**

```bash
# 本地生成（开发调试）
python scripts/runtime_allowlist.py

# 指定路径
python scripts/runtime_allowlist.py \
  --skill-registry skill-registry.yaml \
  --tool-registry  tool-registry.yaml  \
  --output         runtime/allowlist.json
```

**Runtime 消费模式（示例）：**

```python
import json
from pathlib import Path

allowlist = json.loads(Path("runtime/allowlist.json").read_text())

APPROVED_SKILLS = {s["name"] for s in allowlist["skills"]}
APPROVED_TOOLS  = {t["name"]: t for t in allowlist["tools"]}

def route_skill(name: str):
    if name not in APPROVED_SKILLS:
        raise RuntimeError(f"Skill '{name}' not in runtime allowlist")

def get_tool_endpoint(name: str) -> str:
    tool = APPROVED_TOOLS.get(name)
    if not tool:
        raise RuntimeError(f"Tool '{name}' not in runtime allowlist")
    return tool["endpoint"]
```

---

### Phase 6-D · 定时双轨治理巡检（Cron）

**文件：** `.github/workflows/governance-cron.yml`

每周一 08:00 UTC 自动运行，覆盖：
- `governance_audit.py` 全库双轨巡检（S1-S4 + T1-T4 + X1-X3）
- `state_guard.py` 状态机完整性检查
- `runtime_allowlist.py` allowlist 健康检查

所有报告作为 build artifact 保留 90 天。

---

## 资产升降级规则

> 完整规则：`capability-planning/references/asset-promotion-rules.md`

一个能力的形态不是固定的，会随实际使用演化。平台定义 5 条正式升降级路径：

| 方向 | 触发时机 | 核心条件 |
|------|---------|---------|
| **workflow_step → tool** | 发现原子性 + 复用性 | ≥ 2 个 skill 消费；schema 稳定；无业务逻辑 |
| **workflow_step → skill** | 独立治理价值出现 | 满足任意 2 条：跨 agent 复用、需独立 owner、需版本控制… |
| **tool → skill** | 开始积累业务逻辑 | 满足任意 3 条：条件分支、用户触发、协调其他 tool… |
| **skill → tool** | 发现只是单步变换 | 全部满足：仅 1 步、无分支、非用户触发、schema 确定 |
| **tool → workflow_step** | 无消费者，过度抽象 | ≥ 1 个周期无 consumer；逻辑高度耦合某一 skill |

**关键原则**：

- 不做 Tool Admission Gate → skill explosion 会变成 tool explosion
- 升降级决策必须经过 `capability-planning` Phase 0 重新分类
- 降级（skill→tool 或 tool→workflow_step）需在 registry 中标记 `status: deprecated`
  并通知所有消费方

```
演化示例：

[Day 1]  workflow_step: "normalise-alarm-codes"   (在 diagnose-charger-failure 内)
[Month 3] 被 2 个新 skill 需要 → 升级为 tool
[Month 8] tool 开始加入条件判断 + 用户触发 → 升级为 skill
```


---

## 两类 Gate 的本质区别

```
                  Authoring Gate (2S/2T)      Admission Gate (4/4T)
                  ─────────────────────       ──────────────────────
视角              作者视角                    平台视角
目标              检查写得对不对              检查该不该进
关注点            结构、模板、规范             冲突、风险、复用、生态
时机              草稿阶段（提交前）           注册/提交阶段
Skill 工具        validate_skill.py           admission_gate.py
Tool 工具         validate_tool.py            admission_gate_tool.py
输出格式          result + score + blocking_issues  PASS/PASS_WITH_WARNINGS/REQUIRES_REVIEW/REJECT
```

> **Authoring Gate 保证能写，Admission Gate 保证该进。**
> **两轨均已闭环**：Skill（Phase 2S + Phase 4）和 Tool（Phase 2T + Phase 4T）。

**所有 Gate 使用统一结果词汇**（可被 CI / 自动化脚本直接解析）：

| 结果码 | 含义 | Authoring Gate 附加字段 |
|--------|------|------------------------|
| `PASS` | 通过，无需改动 | `score`, `max_score` |
| `PASS_WITH_WARNINGS` | 通过，有建议修改 | `score`, `blocking_issues`, `warnings` |
| `REQUIRES_REVIEW` | 需实质性修改后重新提交 | `score`, `blocking_issues` |
| `REJECT` | 分数过低或违反硬性规则，需重写 | `score`, `blocking_issues` |

---

## 工作流操作手册

### 提交者：上传新 Bundle

1. **克隆仓库**

```bash
git clone https://github.com/hazezhang/skill-registry.git
cd skill-registry
```

2. **（推荐）先进行能力规划**

在本地用 `capability-planning/SKILL.md` 确认 bundle 中哪些是 Skill、哪些是 Tool，
产出 `capability_plan.json` 作为开发依据，避免提交后被大量打回。

3. **创建 orphan 提交分支**（只含 bundle，不含平台文件）

```bash
git checkout --orphan incoming/<my-bundle>
git rm -rf .
git add <my-bundle>/
git commit -m "feat: submit <my-bundle> bundle for admission review"
git push origin incoming/<my-bundle>
```

4. **等待管理员运行准入流程**

如有修改意见，在同一分支上提交修复后再次 push 即可。

---

### 管理员：运行准入流程

```powershell
# 预检（仅查看报告，不合并）
.\skill-intake.ps1 -Bundle <my-bundle>

# 通过后合并到 master
.\skill-intake.ps1 -Bundle <my-bundle> -MergeIfPass
git push origin master
```

脚本执行流程：

1. 检验 `incoming/<bundle>` 分支存在
2. 通过 `git worktree` 在隔离目录读取 bundle 内容
3. 批量运行所有 Skill 的准入检查，报告写入 `reports/`
4. 若无 REJECT/REQUIRES_REVIEW：复制 bundle 并提交到 master
5. 若有阻塞项：输出修改指引，不污染 master

---

### 管理员：日常治理巡检

```bash
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  --update-timestamp

cat reports/manual_review_queue.json
```

---

## Skill 状态机

```
[提交者创建草稿]
      │
      ▼
   draft ──── Phase 2S 校验（validate_skill.py）──── 分数 < 45 → 打回
      │
      ▼ 通过校验
  submitted ── Phase 4 准入（admission_gate.py）
      │
      ├── PASS ──────────────────────────► approved
      ├── PASS_WITH_WARNINGS ────────────► approved / restricted
      ├── REQUIRES_REVIEW ───────────────► needs_revision（人工审核）
      └── REJECT ────────────────────────► draft（返回修改）

[Phase 5 持续治理触发]
approved ──────────────────────────────► deprecated → retired
```

---

## 工具速查

**Skill 相关**

| 场景 | 命令 |
|------|------|
| 校验单个 Skill | `python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md` |
| 校验单个 Skill（JSON） | `python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md --json` |
| 准入检查单个 Skill | `python skill-admission-review/scripts/admission_gate.py <skill>/SKILL.md --registry skill-registry.yaml` |
| 批量准入检查 Bundle | `python scripts/batch_admission.py ev-charger-skills` |
| 运行完整准入流程 | `.\skill-intake.ps1 -Bundle <bundle>` |
| 准入通过后合并 | `.\skill-intake.ps1 -Bundle <bundle> -MergeIfPass` |

**Tool 相关**

| 场景 | 命令 |
|------|------|
| 校验单个 Tool | `python guiding-tool-authoring/scripts/validate_tool.py <tool>/TOOL.md` |
| 校验单个 Tool（JSON） | `python guiding-tool-authoring/scripts/validate_tool.py <tool>/TOOL.md --json` |
| 查看已注册 Tool 列表 | `python -c "import yaml; [print(t['tool_name']) for t in yaml.safe_load(open('tool-registry.yaml',encoding='utf-8'))['tools']]"` |
| Tool 准入检查（单个） | `python tool-admission-review/scripts/admission_gate_tool.py <tool>/TOOL.md --registry tool-registry.yaml` |
| Tool 准入检查（JSON） | `python tool-admission-review/scripts/admission_gate_tool.py <tool>/TOOL.md --registry tool-registry.yaml --json` |

**CI / Runtime**

| 场景 | 命令 |
|------|------|
| 状态机检查 | `python scripts/state_guard.py` |
| 生成 Runtime 白名单 | `python scripts/runtime_allowlist.py` |
| CI 全量检查 | `python scripts/ci_runner.py --all` |
| CI 检查指定文件 | `python scripts/ci_runner.py --files changed.txt` |

**Registry 相关**

| 场景 | 命令 |
|------|------|
| 查看 Skill 总数 | `python -c "import yaml; d=yaml.safe_load(open('skill-registry.yaml',encoding='utf-8')); print(len(d['skills']))"` |
| 查看 Tool 总数 | `python -c "import yaml; d=yaml.safe_load(open('tool-registry.yaml',encoding='utf-8')); print(len(d['tools']))"` |
| 全库治理巡检（双轨） | `python skill-governance-agent/scripts/governance_audit.py --registry skill-registry.yaml --tool-registry tool-registry.yaml --skills-root . --output reports/` |
| 批量修复 frontmatter（预览） | `python scripts/batch_fix_frontmatter.py --dry-run --bundles <bundle>` |
| 批量修复 frontmatter（执行） | `python scripts/batch_fix_frontmatter.py --bundles <bundle>` |

---

## 已知限制与计划改进

### 当前限制

| 项目 | 描述 |
|------|------|
| skill-registry.yaml 状态字段 | 所有已入库 Skill 均为 `approved`，生命周期测试数据（draft/submitted 等）尚未建立 |
| batch_admission.py | 仅控制台输出，无 `--output json` flag |


### 计划改进

- [x] ~~为 Tool 增加 Admission Gate~~ — **已完成** `tool-admission-review/scripts/admission_gate_tool.py`
- [x] ~~`governance_audit.py` 扩展支持 `tool-registry.yaml`~~ — **已完成** S1-S4 + T1-T4 + X1-X3
- [x] ~~统一两个 Gate 的结果词汇表~~ — **已完成** 统一为 PASS / PASS_WITH_WARNINGS / REQUIRES_REVIEW / REJECT
- [ ] `batch_admission.py` 增加 `--output json` flag
- [x] ~~`skill-intake.ps1` 增加 GitHub Actions workflow~~ — **已完成** `.github/workflows/skill-ci.yml`
- [x] ~~Registry 状态字段开始反映真实生命周期~~ — **已完成** `state_guard.py` 强制执行状态机，`runtime_allowlist.py` 按状态过滤

---

## 依赖

```bash
python >= 3.10
pip install pyyaml
```

---

*README 更新于 2026-03-18，反映双轨能力治理体系完整状态（Phase 4T + Phase 5 双轨治理 + Phase 6 CI/Runtime 集成 + 统一 Gate 词汇 + 资产升降级规则）。*
*Skill Registry: 30 个 Skill（3 个平台 meta-skill + 27 个业务 Skill）*
*Tool Registry: 15 个 Tool（均属 bpmn-tools 服务）*
