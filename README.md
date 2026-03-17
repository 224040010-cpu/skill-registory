# Skill Registry — 五阶段闭环治理体系

> **Skill 从"能写出来"到"能稳定进入平台并长期可治理"的完整机制**

---

## 目录

- [体系概览](#体系概览)
- [仓库结构](#仓库结构)
- [五阶段详解](#五阶段详解)
  - [Phase 1 生成](#phase-1--生成)
  - [Phase 2 本地校验](#phase-2--本地校验-authoring-gate)
  - [Phase 3 Registry 注册](#phase-3--registry-注册)
  - [Phase 4 准入门禁](#phase-4--准入门禁-admission-gate)
  - [Phase 5 持续治理](#phase-5--持续治理)
- [两类 Gate 的本质区别](#两类-gate-的本质区别)
- [工作流操作手册](#工作流操作手册)
  - [提交者：上传新 Bundle](#提交者上传新-bundle)
  - [管理员：运行准入流程](#管理员运行准入流程)
  - [管理员：日常治理巡检](#管理员日常治理巡检)
- [Skill 状态机](#skill-状态机)
- [工具速查](#工具速查)
- [已知限制与计划改进](#已知限制与计划改进)

---

## 体系概览

```
Phase 1  生成          Phase 2  本地校验       Phase 3  Registry 注册
  │                       │                       │
  │ guiding-skill-         │ validate_skill.py     │ skill-registry.yaml
  │ authoring              │ (7维度评分)            │ (status: draft)
  │                       │                       │
  ▼                       ▼                       ▼
Phase 4  准入门禁      Phase 5  持续治理
  │                       │
  │ admission_gate.py     │ governance_audit.py
  │ (5项检查)              │ (4类巡检)
  │                       │
  ▼                       ▼
status: approved      daily/weekly report
                      manual_review_queue.json
```

**三个核心问题**

| 问题 | 解决阶段 |
|------|---------|
| Skill 写出来但结构不完整、边界不清、描述不可路由 | Phase 1 + Phase 2 |
| Skill 写得像样但不适合进入平台 | Phase 4 |
| Skill 进入仓库后会漂移、重复、过期、失效 | Phase 5 |

---

## 仓库结构

```
skill-registry/
│
├── skill-registry.yaml              # Phase 3: 中央注册表（41 个 Skill）
├── skill-intake.ps1                 # 管理员准入工作流脚本
│
├── guiding-skill-authoring/         # Phase 1: 生成指导 meta-skill
│   ├── SKILL.md
│   ├── scripts/
│   │   └── validate_skill.py        # Phase 2: 7维度评分校验器
│   ├── references/
│   │   ├── validation-rubric.md
│   │   ├── mcp-tool-catalog.md
│   │   ├── naming-guide.md
│   │   └── platform-constraints.md
│   └── assets/
│       └── skill-template.md
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
│   ├── batch_admission.py           # 批量运行准入检查
│   ├── batch_fix_frontmatter.py     # 批量修复 frontmatter 字段
│   └── fix_risk_levels.py           # 批量升级 risk_level
│
├── reports/                         # 自动生成的报告
│   ├── admission_<bundle>.txt
│   ├── governance_report_YYYYMMDD.json
│   └── manual_review_queue.json
│
├── ev-charger-skills/               # 已入库 Bundle（24 个 Skill）
└── business-to-bpmn/                # 已入库 Bundle（16 个 Skill）
```

**Git 分支结构**

```
master                          ← 平台基础设施 + 已入库 Skill
incoming/<bundle>               ← 提交者专用，仅含 bundle 目录（orphan branch）
```

---

## 五阶段详解

### Phase 1 · 生成

**目标**：把"业务想法"转成"结构化 Skill 草稿"

**执行者**：`guiding-skill-authoring/SKILL.md`（meta-skill，由 AI Agent 调用）

**8 问意图采集**

在生成草稿前，先通过结构化问卷确认：

1. 这个 Skill 解决什么业务问题？
2. 触发场景是什么？（用户说什么时调用）
3. 不触发场景是什么？
4. 所属 Agent 是哪个？（`bundle_scope`）
5. 是否需要设备控制？（影响 `risk_level`）
6. 是否有语音播报要求？（影响 TTS 约束）
7. 需要哪些输入参数？
8. 输出什么？

**产出**

- 一份完整的 `SKILL.md` 草稿（含 frontmatter + 四节 body）
- 职责范围确认句
- 初步 `risk_level` 和 `bundle_scope`
- `skill-registry.yaml` stanza 草稿

> **这一层只回答**："这个 Skill 能不能被写出来、怎么写出来"
> **不回答**："它该不该进平台"

---

### Phase 2 · 本地校验（Authoring Gate）

**目标**：在提交前挡住结构性错误

**执行者**：`guiding-skill-authoring/scripts/validate_skill.py`

**7 个评分维度（满分 70）**

| # | 维度 | 满分 | 核心检查项 |
|---|------|------|-----------|
| 1 | Trigger Clarity | 10 | 第三人称、`Use when`、`Do NOT use when`、模糊词惩罚 |
| 2 | Workflow Executability | 10 | `[ ] Step N:` 格式、`server:tool_name()` 调用、异常分支 |
| 3 | MCP Tool Compliance | 10 | 工具引用注册验证、L4 需有 Verify Gate |
| 4 | Input/Output Contract | 10 | 明确输入参数、输出定义、TTS 约束（若声明 voice 平台） |
| 5 | Constraints & Safety | 10 | `# Constraints` 节、NEVER 声明、作用域声明、必填输出字段 |
| 6 | Single Responsibility | 10 | 无连词过载、无跨 Skill 调用、无混合输出类型 |
| 7 | Testability | 10 | 输入输出示例、边界案例、`evals/evals.json` |

**判定标准**

```
≥ 60 / 70  → PASS（可提交）
≥ 45 / 70  → PASS_WITH_REQUIRED_FIXES（有条件通过，须修复 blocking issues）
< 45 / 70  → FAIL（打回修改）
有任何 blocking issue → 不得提交
```

**使用方法**

```bash
# 标准输出（人类可读）
python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md

# JSON 输出（用于自动化）
python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md --json
```

**JSON 输出格式**

```json
{
  "skill_name": "diagnosing-charger-faults",
  "score": 61,
  "result": "PASS",
  "blocking_issues": [],
  "warnings": ["Add an error or edge case example"],
  "suggestions": ["[Meta-skill] Dim 3 exempt..."]
}
```

> **这一层是创作质量门**：检查 Skill 写得对不对，不判断该不该进平台。

---

### Phase 3 · Registry 注册

**目标**：让 Skill 进入统一管理系统，而不是散落在仓库里

**文件**：`skill-registry.yaml`

**必填字段**

```yaml
- skill_name: diagnosing-charger-faults     # 与目录名和 SKILL.md name 一致
  display_name: "Diagnosing Charger Faults"
  purpose: "一句话描述，用于路由匹配"
  owner_team: ev-charger
  version: "1.0.0"
  status: draft                              # 初始状态
  risk_level: L2                             # L1-L4
  dependencies: []                           # 依赖的其他 Skill
  bundle_scope: diagnosis-agent              # 所属 Agent
  supported_models:
    - claude-sonnet-4-6
  eval_status: pending                       # pending | passing | failing
  security_review: not_required              # L4 必须为 pending 或 approved
  path: ev-charger-skills/diagnosing-charger-faults/SKILL.md
  created_at: "2026-03-17"
  last_reviewed: "2026-03-17"
```

**状态生命周期**

```
draft → submitted → approved
                 → restricted
                 → needs_revision
approved → deprecated → retired
```

**注册时机**

建议通过 Authoring Gate 后以 `draft` 状态先入 Registry，再走 Admission Gate。
**不要等批准后才登记**——否则会失去统一跟踪能力。

> **这一层是资产登记，不是上线批准。**

---

### Phase 4 · 准入门禁（Admission Gate）

**目标**：从平台视角判断"这个 Skill 该不该正式进入平台"

**执行者**：`skill-admission-review/scripts/admission_gate.py`

**5 项检查**

| # | 检查项 | 关键判定 |
|---|--------|---------|
| 1 | **全局冲突检查** | 同名 → REJECT；编辑距离 ≤2 → WARNING；Jaccard 相似度 >0.65 → REQUIRES_REVIEW |
| 2 | **Agent 边界检查** | `bundle_scope` 缺失/无效 → REJECT；跨 Agent 词汇污染 → REQUIRES_REVIEW/WARNING |
| 3 | **风险等级检查** | Workflow 节中含设备控制词但非 L4 → REJECT；L1 含写操作词 → REQUIRES_REVIEW |
| 4 | **路由治理检查** | 描述过短/无触发子句/含模糊词 → WARNING；描述过宽泛 → REQUIRES_REVIEW |
| 5 | **形态合理性检查** | 调用其他 Skill → REJECT；步骤过少无异常处理 → WARNING（建议注册为 MCP Tool） |

**4 种准入决策**

| 决策 | 含义 | 建议操作 |
|------|------|---------|
| `PASS` | 可正式进入 Registry | 更新 `status: approved` |
| `PASS_WITH_WARNINGS` | 可进入，有治理提醒 | 更新为 `approved` 或 `restricted`，跟踪 warnings |
| `REQUIRES_REVIEW` | 需人工审核 | 更新为 `needs_revision`，指派审核 |
| `REJECT` | 不适合准入 | 保持 `draft`，返回修改意见 |

**使用方法**

```bash
# 单个 Skill
python skill-admission-review/scripts/admission_gate.py <skill>/SKILL.md --registry skill-registry.yaml

# 整个 Bundle（批量）
python scripts/batch_admission.py ev-charger-skills business-to-bpmn
```

**JSON 输出格式**

```json
{
  "skill_name": "diagnosing-charger-faults",
  "decision": "PASS_WITH_WARNINGS",
  "reasons": ["Moderate description overlap with 'log-analyzer' (Jaccard=0.47)"],
  "recommended_actions": ["Verify these skills have clearly distinct trigger conditions"],
  "neighbor_skills": ["log-analyzer"],
  "check_details": {
    "global_conflict": "WARNING",
    "agent_boundary": "PASS",
    "risk_level": "PASS",
    "routing_governance": "PASS",
    "form_factor": "PASS"
  }
}
```

> **这一层是平台治理门**：检查 Skill 该不该进，不管 Skill 写得对不对。

---

### Phase 5 · 持续治理

**目标**：让治理从一次性准入变成持续过程

**执行者**：`skill-governance-agent/scripts/governance_audit.py`

**4 类巡检**

| 类型 | 检查内容 | 严重级别 |
|------|---------|---------|
| **仓库一致性** | 仓库有而 Registry 无；Registry 有而仓库无；name 字段与 registry 不一致 | HIGH / WARNING |
| **元数据健康** | 必填字段缺失；`purpose` 过短/含模糊词；命名不规范；Eval 长期 pending；`eval_status: failing` | HIGH / WARNING |
| **冲突漂移** | 已上线 Skill 间 purpose 相似度漂移（Jaccard 持续监控）；同命名家族过载 | HIGH / WARNING |
| **生命周期** | 审查超期（180天）；L4 安全审查逾期（30天）→ CRITICAL；failing evals 90天无处理；上线满一年无复查 | CRITICAL / HIGH / WARNING |

**报告输出**

```bash
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  [--update-timestamp]
```

生成两个文件：

- `reports/governance_report_YYYYMMDD.json` — 完整巡检报告
- `reports/manual_review_queue.json` — 需人工处理的 HIGH/CRITICAL 项

**自动操作白名单**（脚本可直接执行，无需人工确认）

- 更新 `last_audited` 时间戳
- 生成 governance report
- 生成 manual_review_queue

**禁止自动执行**（必须人工操作）

- 删除 Skill
- 修改 description / risk_level / bundle_scope
- 自动批准上线

---

## 两类 Gate 的本质区别

```
                  Authoring Gate              Admission Gate
                  ─────────────────           ──────────────────
视角              作者视角                    平台视角
目标              检查 Skill 写得对不对        检查 Skill 该不该进
关注点            结构、模板、规范             冲突、风险、生态合理性
时机              草稿阶段（提交前）           注册/提交阶段
工具              validate_skill.py           admission_gate.py
输出              分数 + blocking issues      准入决策 + 状态流转
输出格式          score: 0-70                 PASS/WARN/REVIEW/REJECT
```

一句话概括：
> **Authoring Gate 保证能写，Admission Gate 保证该进。**

---

## 工作流操作手册

### 提交者：上传新 Bundle

1. **克隆仓库**

```bash
git clone https://github.com/hazezhang/skill-registry.git
cd skill-registry
```

2. **创建 orphan 提交分支**（只含 bundle，不含平台文件）

```bash
git checkout --orphan incoming/<my-bundle>
git rm -rf .                    # 清空暂存区，从零开始

# 放入你的 bundle 目录
git add <my-bundle>/
git commit -m "feat: submit <my-bundle> bundle for admission review"
git push origin incoming/<my-bundle>
```

3. **等待管理员运行准入流程**

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

1. 检验 `incoming/<bundle>` 分支存在（本地或远端）
2. 通过 `git worktree` 在隔离目录读取 bundle 内容
3. 批量运行所有 Skill 的准入检查，报告写入 `reports/`
4. 若无 REJECT/REQUIRES_REVIEW：复制 bundle 到工作区并提交
5. 若有阻塞项：输出修改指引，不污染 master

---

### 管理员：日常治理巡检

```bash
# 全库巡检
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  --update-timestamp

# 查看需人工处理的项
cat reports/manual_review_queue.json
```

---

## Skill 状态机

```
[提交者创建草稿]
      │
      ▼
   draft ──── Phase 2 校验（validate_skill.py）──── 分数 < 45 → 打回修改
      │
      ▼ 通过校验
  submitted ── Phase 4 准入（admission_gate.py）
      │
      ├── PASS ──────────────────────────► approved
      │
      ├── PASS_WITH_WARNINGS ────────────► approved / restricted
      │
      ├── REQUIRES_REVIEW ───────────────► needs_revision（人工审核）
      │
      └── REJECT ────────────────────────► draft（返回修改）

[Phase 5 持续治理触发]
approved ──────────────────────────────► deprecated → retired
```

---

## 工具速查

| 场景 | 命令 |
|------|------|
| 校验单个 Skill（人类可读） | `python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md` |
| 校验单个 Skill（JSON） | `python guiding-skill-authoring/scripts/validate_skill.py <skill>/SKILL.md --json` |
| 准入检查单个 Skill | `python skill-admission-review/scripts/admission_gate.py <skill>/SKILL.md --registry skill-registry.yaml` |
| 批量准入检查整个 Bundle | `python scripts/batch_admission.py ev-charger-skills` |
| 运行完整准入流程 | `.\skill-intake.ps1 -Bundle <bundle>` |
| 准入通过后合并到 master | `.\skill-intake.ps1 -Bundle <bundle> -MergeIfPass` |
| 验证注册表条目数 | `python -c "import yaml; d=yaml.safe_load(open('skill-registry.yaml')); print(len(d['skills']))"` |
| 全库治理巡检 | `python skill-governance-agent/scripts/governance_audit.py --registry skill-registry.yaml --skills-root . --output reports/` |
| 批量修复 frontmatter（预览） | `python scripts/batch_fix_frontmatter.py --dry-run --bundles <bundle>` |
| 批量修复 frontmatter（执行） | `python scripts/batch_fix_frontmatter.py --bundles <bundle>` |

---

## 已知限制与计划改进

### 当前限制

| 项目 | 描述 |
|------|------|
| validate_skill.py 结果词汇 | 输出 `PASS_WITH_REQUIRED_FIXES`，与 Admission Gate 的 `PASS_WITH_WARNINGS` 词汇不统一 |
| validate_skill.py 解析器 | 自定义简易 YAML 解析器，多行 description 会被合并为单行，影响少数情况下的评分准确性 |
| skill-registry.yaml 状态字段 | 所有 41 个已入库 Skill 均为 `approved`，生命周期状态机已定义但尚未用于实际数据管控 |
| batch_admission.py 输出 | 仅控制台输出，无 `--output` / `--json` flag；`--registry` 路径硬编码 |
| skill-intake.ps1 | 仅支持本地手动运行，尚无 GitHub Actions / CI 集成 |
| batch_fix_frontmatter.py | 仅注入 `bundle_scope` 和 `risk_level` 两个字段，无 `--field` 选择器 |

### 计划改进

- [ ] 统一两个 Gate 的结果词汇表
- [ ] `batch_admission.py` 增加 `--output json` flag，支持结构化报告落文件
- [ ] `skill-intake.ps1` 增加 GitHub Actions workflow，实现 PR 自动触发准入检查
- [ ] Registry 状态字段开始反映真实生命周期（已有机制，需落实到操作流程）
- [ ] `governance_audit.py` 增加 `--since` 参数，支持增量巡检

---

## 依赖

```bash
# 必需
python >= 3.10

# 推荐（部分脚本有内置 fallback）
pip install pyyaml
```

---

*README 自动生成于 2026-03-17，基于当前仓库状态完整审计。*
