# guiding-skill-authoring

**类型：** 元 Skill（Meta Skill）｜**风险等级：** L1｜**状态：** Draft

引导业务人员和工程师完成 EV 充电站 Agent 平台 Skill 的全生命周期创作——从意图采集、草稿撰写、MCP 合规校验，到 Registry 注册和提交前检查。

---

## 适用场景

当你遇到以下情况时，使用本 Skill：

- 想为平台**新建一个 Skill**，不知道从哪里开始
- 已有业务流程，想判断**能否做成 Skill**（或需要拆分）
- 写好了 SKILL.md 草稿，需要**校验是否符合平台规范**
- 需要了解**命名规则、Trigger 写法、MCP 工具引用格式**
- 准备提交 PR，需要**完整的 Pre-Submission Checklist**

**不适用：**
- 询问某个已有 Skill 的运行逻辑（去看那个 Skill 本身）
- 调用或执行某个已有 Skill
- 与 Skill 创作无关的 Agent 架构问题

---

## 快速开始

### 新建一个 Skill

```
1. 告诉 Agent 你想做什么（一句话描述）
   → Agent 会引导你完成 Phase 1 意图采集（8 个问题）
   → 确认一句话职责范围后，进入草稿生成

2. Agent 根据你的回答生成 SKILL.md 草稿
   → 草稿基于 assets/skill-template.md 生成

3. 运行校验脚本
   python skills/guiding-skill-authoring/scripts/validate_skill.py \
     skills/<your-skill-name>/SKILL.md

4. 根据报告修复 blocking issues，评分 ≥ 45 提交 PR
```

### 只校验一个已有草稿

```bash
python skills/guiding-skill-authoring/scripts/validate_skill.py skills/<your-skill>/SKILL.md
```

输出：7 维度评分报告 + blocking issues + 改进建议

退出码：`0` = 通过（≥45分），`1` = 需要修改，`2` = 解析失败

---

## 5 阶段创作流程

| 阶段 | 内容 | 产出 |
|------|------|------|
| **Phase 1** 意图采集 | 8 个结构化问题，明确职责边界 | 一句话范围确认 |
| **Phase 2** 起草 Skill | 套用模板，填写 Workflow/Constraints | SKILL.md 草稿 |
| **Phase 3** 校验 | 运行脚本 + 7 维度 Rubric | 评分报告 |
| **Phase 4** Registry 注册 | 填写 skill-registry.yaml 条目 | YAML 注册条目 |
| **Phase 5** 提交检查 | Pre-Submission Checklist | 可提交的 PR |

---

## 校验评分标准

| 分数 | 结论 |
|------|------|
| ≥ 60 | 直接通过，无需必要修改 |
| 45–59 | 条件通过，有必要修改项 |
| 30–44 | 需要大幅修改 |
| < 30 | 需要重写 |

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 主 Skill 文件，Agent 加载的全部指导内容 |
| `assets/skill-template.md` | 可直接填写的 SKILL.md 模板，新建 Skill 时复制使用 |
| `scripts/validate_skill.py` | 自动化校验脚本，支持 `meta_skill: true` 豁免逻辑 |
| `evals/evals.json` | 5 个自动化测试用例（创作引导/校验/拆分/L4/Skill 隔离） |
| `references/platform-constraints.md` | 平台完整约束：TTS 规则、Verify Gate 流程、Agent 边界、Skill 隔离 |
| `references/mcp-tool-catalog.md` | 全部已注册 MCP 工具，含签名和风险等级 |
| `references/validation-rubric.md` | 7 维度质量评分细则，含 EV 领域示例和评分指导 |
| `references/naming-guide.md` | 动词分类、25+ 领域命名示例、Description 公式示例 |

---

## 关于元 Skill

本 Skill 声明了 `meta_skill: true`，代表它是**指导型 Skill**，而不是执行业务操作的 Skill：

- **不调用任何 MCP 工具**（L1，无副作用）
- **产出为文档**：SKILL.md 草稿、校验报告、Registry 条目
- `validate_skill.py` 对 `meta_skill: true` 的 Skill 豁免 Dimension 2（Workflow 可执行性）和 Dimension 3（MCP 工具合规）的 MCP 工具检查

---

## Registry 信息

```yaml
skill_name: guiding-skill-authoring
display_name: Skill 创作向导
risk_level: L1
bundle_scope: [diagnosis-agent, customer-agent, ops-agent, energy-agent]
status: draft
```
