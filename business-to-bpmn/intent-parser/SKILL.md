---
name: intent-parser
description: Parses user natural language business descriptions into structured intent (business_type, goal, constraints, scope). Only does semantic understanding, no decision-making. Use when intent parsing, 意图解析, 解析业务意图, or extracting business intent from user descriptions in business-to-bpmn pipeline.
---

# Intent Parser

将用户自然语言描述解析为结构化意图（业务类型、目标、约束条件）。仅做语义理解，不做决策或后续规划。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 理解层第一步，需要从用户描述得到结构化意图
- 用户明确要求「意图解析」「解析业务意图」「提取业务意图」「extract business intent」

**Do NOT use this Skill when:**
- 已有结构化意图，需要抽取实体（用 entity-extractor）
- 需要识别歧义或生成澄清问题（用 ambiguity-detector）
- 需要选模板、拆步骤或生成 BPMN（属规划层/建模层）

## Instructions

1. **Read the full user description** — 完整读取用户自然语言业务描述（当前轮次或上文）
2. **Identify business_type** — 识别业务类型：approval、data-sync、alert-handling、reporting、order-processing、ticket-routing 等
3. **Extract the goal** — 提取流程应达成的目标（what the process should achieve）
4. **List constraints** — 列举约束条件：时限、审批层级、重试策略、角色限制等
5. **Determine scope** — 确定范围：涉及的系统、部门、设备等
6. **Output structured intent JSON** — 输出符合 schema 的 JSON，格式见 `references/api-reference.md`

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| user_description | string | 用户自然语言业务描述 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| business_type | string | 业务类型 |
| goal | string | 流程目标 |
| constraints | string[] | 约束条件列表 |
| scope | string | 范围说明 |

## Example

**Input:**
```json
{
  "user_description": "设计一个充电桩告警诊断与自恢复流程：设备端检测到异常后上报告警，云端Agent分析告警类型，低风险的自动执行恢复命令，高风险的转人工确认后再执行"
}
```

**Output:**
```json
{
  "business_type": "alert-handling",
  "goal": "充电桩告警自动诊断与分级恢复",
  "constraints": ["低风险自动恢复", "高风险需人工确认"],
  "scope": "设备端 + 云端Agent"
}
```

## References

- 能力概述：See `references/overview.md`
- 详细 I/O Schema：See `references/api-reference.md`

## Constraints

- 仅基于当前输入文本推断，不猜测未提及内容
- 约束条件从原文显式或合理隐含中抽取，不擅自增加
- 输出后不调用其他 skill，由编排层决定下一步（通常为 entity-extractor）
