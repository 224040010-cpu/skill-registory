---
name: bpmn-template-matcher
description: Matches structured intent against BPMN workflow template library. Outputs candidate list and similarity scores. Only does template retrieval and scoring, no customization. Use when template matching, 模板匹配, 模板检索, or deciding whether to use a template shortcut in business-to-bpmn planning layer.
bundle_scope: bpmn-agent
risk_level: L1
---

# BPMN Template Matcher

根据结构化意图检索并匹配 BPMN 工作流模板，输出候选列表与相似度评分。仅做模板检索与打分，不做模板定制或步骤修改。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 规划层入口，意图已就绪，需决定是否走模板捷径
- 用户明确要求「模板匹配」「模板检索」「找 BPMN 模板」

**Do NOT use this Skill when:**
- 需要拆步骤、算依赖或生成 BPMN 元素（属 process-decomposer、dependency-resolver、bpmn-element-mapper）

## Instructions

1. **Read intent** — 读取 intent-parser 输出的结构化意图（business_type, goal, constraints, scope）
2. **Compare against template categories** — 将 business_type 与已知模板类别比对：approval、data-sync、alert-handling、reporting、onboarding、order-processing
3. **Score similarity** — 基于 goal 对齐度、constraint 匹配度、scope 重叠度计算相似度
4. **Return top 3 candidates** — 按 score 降序输出最多 3 个候选
5. **Set best_match** — 若最高分 ≥ 0.8，best_match 为该候选；若无 ≥ 0.5 的匹配，best_match 为 null

## Known Template Categories

| 类别 | 典型模式 |
|------|----------|
| approval | submit → review → approve/reject → (loop back or proceed) |
| alert-handling | detect → analyze → classify → handle → verify → report |
| data-sync | trigger → extract → transform → load → verify |
| order-processing | create → validate → process → fulfill → notify |

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| intent | IntentOutput | intent-parser 输出（business_type, goal, constraints, scope） |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| candidates | TemplateCandidate[] | 候选模板列表，按 similarity_score 降序 |
| best_match | { template_id, similarity_score } \| null | 最高分 ≥ 0.8 时非空；无 ≥ 0.5 时为 null |

**TemplateCandidate**：`{ template_id: string, template_name: string, similarity_score: number, description: string }`

## Example

**Input:**
```json
{
  "intent": {
    "business_type": "alert-handling",
    "goal": "充电桩告警自动诊断与分级恢复",
    "constraints": ["低风险自动恢复", "高风险需人工确认"],
    "scope": "设备端 + 云端Agent"
  }
}
```

**Output:**
```json
{
  "candidates": [
    {
      "template_id": "tpl_alert_01",
      "template_name": "告警分级处理",
      "similarity_score": 0.85,
      "description": "告警检测→分析→分级→自动/人工处理→验证→报告"
    }
  ],
  "best_match": {
    "template_id": "tpl_alert_01",
    "similarity_score": 0.85
  }
}
```

## Orchestrator Behavior

- **best_match score ≥ 0.8**：编排层以该模板为基础进入 BPMN 建模层
- **best_match 为 null**：编排层依次调用 process-decomposer → dependency-resolver → parallel-optimizer

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 不改写模板内容；模板库来源由实现方定义
- 仅做检索与打分，不生成步骤或 DAG
