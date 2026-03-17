---
name: intent-coverage-evaluator
description: Evaluates whether the generated BPMN workflow covers the original user intent. Compares workflow elements against extracted intent and entities. Only evaluates, does not modify. Use when coverage evaluation, 覆盖度评估, 意图对齐, or 需求覆盖.
---

# Intent Coverage Evaluator

评估 BPMN 工作流对原始用户意图的覆盖度，输出覆盖度评分、已覆盖项和缺失项。仅做意图对齐评估，不修改工作流。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 验证层，BPMN XML 已生成，需要评估是否满足原始需求
- 用户明确要求「覆盖度评估」「意图对齐」「需求覆盖」

**Do NOT use this Skill when:**
- 需要校验 XML 结构或逻辑（用 bpmn-compliance-validator）
- 需要修改 BPMN（用 bpmn-diagram-optimizer 或 bpmn-xml-serializer）

## Instructions

1. **Parse BPMN XML** to extract all task names, event names, gateway conditions

2. **Compare against original intent:**
   - Is the goal achieved by the process flow?
   - Are all constraints represented (as gateway conditions, timer events, etc.)?

3. **Compare against original entities:**
   - Are all roles represented (as lanes or task performers)?
   - Are all systems represented (as participants or service tasks)?
   - Are all data objects handled (as data inputs/outputs)?
   - Are all triggers represented (as start events)?

4. **Calculate coverage_score** = covered_items.length / (covered_items.length + missing_items.length)

5. **Generate recommendations** for missing items

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| bpmn_xml | string | BPMN 2.0 XML 字符串 |
| original_intent | IntentOutput | intent-parser 输出 |
| original_entities | EntityOutput | entity-extractor 输出 |

**IntentOutput:** `{ business_type: string, goal: string, constraints: string[], scope?: string }`

**EntityOutput:** `{ roles: Entity[], systems: Entity[], data_objects: Entity[], triggers: Entity[] }`

**Entity:** `{ id: string, name: string, description: string }`

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| coverage_score | number | 覆盖度评分（0–1） |
| covered_items | string[] | 已覆盖项列表 |
| missing_items | string[] | 缺失项列表 |
| recommendations | string[] | 改进建议列表 |

## Example

**Input:**
```json
{
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "original_intent": {
    "business_type": "alert-handling",
    "goal": "充电桩告警自动诊断与分级恢复",
    "constraints": ["低风险自动恢复", "高风险人工确认", "恢复失败需升级"],
    "scope": "设备端与云端Agent"
  },
  "original_entities": {
    "roles": [{ "id": "role_1", "name": "运维人员", "description": "人工确认" }],
    "systems": [
      { "id": "sys_1", "name": "设备端", "description": "充电桩" },
      { "id": "sys_2", "name": "云端Agent", "description": "多模态Agent" }
    ],
    "data_objects": [{ "id": "data_1", "name": "告警", "description": "告警数据" }],
    "triggers": [{ "id": "trigger_1", "name": "告警触发", "description": "设备上报" }]
  }
}
```

**Output:**
```json
{
  "coverage_score": 0.85,
  "covered_items": [
    "告警检测",
    "告警分析",
    "风险分级",
    "自动恢复",
    "人工确认"
  ],
  "missing_items": [
    "恢复失败升级路径",
    "告警统计报表"
  ],
  "recommendations": [
    "添加错误边界事件处理恢复失败场景",
    "添加报表生成 serviceTask"
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅做意图对齐评估，不修改 BPMN
- coverage_score 为 0–1 浮点数，1 表示完全覆盖
