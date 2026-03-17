---
name: entity-extractor
description: Extracts key entities (roles, systems, data objects, triggers) from user description and intent structure. Only does entity identification, no association reasoning. Use when entity extraction, 实体抽取, 提取角色和系统, or extracting roles/systems/data objects/triggers in business-to-bpmn pipeline.
---

# Entity Extractor

从用户描述与意图结构中抽取关键实体（角色、系统、数据对象、触发条件）。仅做实体识别与列举，不做关联推理或依赖分析。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 理解层第二步，已有 intent-parser 输出，需要实体列表
- 用户明确要求「实体抽取」「提取角色和系统」「列出数据对象和触发条件」

**Do NOT use this Skill when:**
- 尚未有结构化意图（先用 intent-parser）
- 需要识别歧义或生成澄清问题（用 ambiguity-detector）
- 需要拆步骤或生成 BPMN（属规划层/建模层）

## Instructions

1. **Scan description for role mentions** — 扫描描述中的人、部门、系统等角色
2. **Identify systems** — 识别系统：平台、服务、设备等
3. **Extract data objects** — 抽取数据对象：工单、报告、告警、订单等
4. **Identify triggers** — 识别触发条件：启动流程的事件
5. **Assign unique IDs** — 为每个实体分配唯一 ID：role_1、sys_1、data_1、trigger_1

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| user_description | string | 用户自然语言业务描述 |
| intent | IntentOutput | intent-parser 输出（business_type, goal, constraints, scope） |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| roles | Entity[] | 角色列表 |
| systems | Entity[] | 系统列表 |
| data_objects | Entity[] | 数据对象列表 |
| triggers | Entity[] | 触发条件列表 |

**Entity 结构**：`{ id: string, name: string, description: string }`

## Example

**Input:**
```json
{
  "user_description": "设备端检测到异常后上报告警，云端Agent分析告警类型，低风险的自动执行恢复命令，高风险的转人工确认后再执行",
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
  "roles": [
    { "id": "role_1", "name": "设备端", "description": "充电桩设备" }
  ],
  "systems": [
    { "id": "sys_1", "name": "云端Agent", "description": "云端多模态Agent平台" }
  ],
  "data_objects": [
    { "id": "data_1", "name": "告警信息", "description": "设备异常告警数据" }
  ],
  "triggers": [
    { "id": "trigger_1", "name": "异常检测", "description": "设备检测到充电异常" }
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- 详细 I/O Schema：See `references/api-reference.md`

## Constraints

- 实体仅从描述与意图中抽取，不虚构
- 同一实体只出现一次，命名一致
- 输出后不调用其他 skill，由编排层决定下一步（通常为 ambiguity-detector）
