---
name: business-to-bpmn
description: |
  将用户自然语言业务描述直接转化为符合 BPMN 2.0 标准的工作流 XML（含泳道、消息流、自动布局与视觉美化），可在 bpmn.io 或 Camunda 中直接打开。
  Use when the user describes a business scenario and wants a BPMN workflow — including phrases like "生成BPMN", "业务转工作流", "设计流程", "把需求转成BPMN", "审批流程", "自动化流程", "SOP转BPMN", "生成.bpmn文件", or any request to convert business descriptions into BPMN 2.0 XML. Also trigger on "帮我画个流程", "工作流标准化", "业务流程建模", "流程自动化", "我有个业务场景想变成工作流", even without explicitly mentioning "BPMN".
---

# Purpose

本 Skill 负责**编排**「业务描述 → BPMN 2.0 工作流」全链路流水线：按 5 层分层策略调用 15 个原子 skill，从自然语言直达可执行 BPMN XML，无需中间格式转换。

# Trigger

**Use this Skill when:**
- 用户提供业务场景描述，期望得到 BPMN 标准工作流
- 用户要求将业务规则、SOP、审批流程转为 BPMN 2.0 XML
- 用户提到「从需求生成 BPMN」「业务流程建模」「生成 .bpmn 文件」等

**Do NOT use this Skill when:**
- 用户已有 Mermaid 流程图想转 BPMN（应使用 flowchart-to-bpmn）
- 用户只想生成 JSON/YAML 工作流定义，不需要 BPMN 格式（应使用 workflow-from-business）
- 用户要修改或调试已有 .bpmn 文件

# Architecture

5 层 15 技能流水线，直达 BPMN 2.0 输出：

```
用户业务描述
    ↓
[Layer 1: 理解层]  intent-parser → entity-extractor → ambiguity-detector
    ↓                                    ↑ (有歧义则返回用户澄清后重跑)
[Layer 2: 规划层]  bpmn-template-matcher → process-decomposer → dependency-resolver → parallel-optimizer
    ↓               ↓ (命中模板则跳过 decomposer/resolver/optimizer)
[Layer 3: BPMN建模层]  bpmn-element-mapper → bpmn-task-classifier → bpmn-model-assembler → bpmn-participant-organizer
    ↓
[Layer 4: BPMN渲染层]  bpmn-xml-serializer → bpmn-diagram-optimizer
    ↓
[Layer 5: 验证层]  bpmn-compliance-validator → intent-coverage-evaluator
    ↓                    ↑ (不通过则回到对应层修正)
输出 .bpmn 文件
```

# Workflow

- [ ] Step 1：**理解层** — 依次调用 intent-parser → entity-extractor → ambiguity-detector；若返回澄清问题则呈现给用户，等待回复后重跑理解层
- [ ] Step 2：**规划层** — 调用 bpmn-template-matcher；若命中高相似度模板（≥0.8）则以模板为基础进入 Step 3，否则依次调用 process-decomposer → dependency-resolver → parallel-optimizer
- [ ] Step 3：**BPMN建模层** — 调用 bpmn-element-mapper 将步骤映射为 BPMN 元素，再调用 bpmn-task-classifier 确定任务子类型，然后 bpmn-model-assembler 组装流程模型，最后 bpmn-participant-organizer 分配泳道与池
- [ ] Step 4：**BPMN渲染层** — 调用 bpmn-xml-serializer 序列化为 BPMN 2.0 XML，再调用 bpmn-diagram-optimizer 执行自动布局、视觉美化和标签优化
- [ ] Step 5：**验证层** — 调用 bpmn-compliance-validator 做结构与逻辑校验，调用 intent-coverage-evaluator 评估意图覆盖度；若有严重错误或覆盖度 < 0.7 则回到对应层修正后重跑后续步骤
- [ ] Step 6：**输出** — 将最终 .bpmn 文件写入指定目录，附验证摘要

# Key Design Decisions

**为什么不复用 workflow-from-business + flowchart-to-bpmn？**
- 两组串联需 27 个 skill（13 + 14），中间经过 JSON/Mermaid 格式转换，信息损失大
- 规划层不感知 BPMN 语义（如网关类型、事件类型），导致后期大量修正
- 本 skill 组让规划层直接产出 BPMN-aware 的步骤定义，减少从 15 个 skill 一步到位

**为什么合并渲染子步骤？**
- 原 flowchart-to-bpmn 将布局、样式、标签分为 3 个独立 skill，实际运行中三者高度耦合
- 合并为 bpmn-diagram-optimizer 单一 skill，减少层间传递开销，同时保持内部分步处理

# References

- 能力概述与编排策略：See `references/overview.md`
- 各原子 skill 输入输出与职责：See `references/api-reference.md`
- 异常处理与常见问题：See `references/troubleshooting.md`

# Examples

**Example 1 — 充电桩告警处理流程:**
Input: "设计一个充电桩告警诊断与自恢复流程：设备端检测到异常后上报告警，云端Agent分析告警类型，低风险的自动执行恢复命令，高风险的转人工确认后再执行，执行后验证恢复结果并生成报告"
Output: charging-alarm.bpmn，含 startEvent（告警触发）、serviceTask（告警分析）、exclusiveGateway（风险级别判断）、userTask（人工确认）、serviceTask（执行恢复）、serviceTask（结果验证）、endEvent，2 个泳道（设备端/云端Agent），消息流连接

**Example 2 — 工单审批流程:**
Input: "员工提交工单，主管审批，不通过则退回修改，通过后系统自动分配工程师"
Output: work-order.bpmn，含 startEvent、userTask（提交工单）、userTask（主管审批）、exclusiveGateway（通过/不通过）、serviceTask（自动分配）、endEvent，回环路径（退回→重新提交）

# Constraints

- 理解层必须先完成再进入规划层，因为实体和意图是 BPMN 元素映射的基础，跳过会导致泳道分配错误、任务类型误判
- 每个原子 skill 专注自身职责，skill 间通过结构化数据传递，不直接调用其他 skill
- 引用深度仅一层（本 SKILL.md → references/*.md），避免上下文膨胀

# Dependencies

Environment: Cursor IDE (filesystem access required)
Required packages: None (pure XML generation)
MCP servers required: None
