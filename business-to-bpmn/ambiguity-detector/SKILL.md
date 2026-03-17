---
name: ambiguity-detector
description: Based on intent and entity list, identifies ambiguities and generates user-facing clarification questions. Only identifies uncertain items, does not make assumptions. Use when ambiguity detection, 歧义检测, 澄清问题生成, or generating clarification questions before planning in business-to-bpmn pipeline.
bundle_scope: bpmn-agent
risk_level: L2
---

# Ambiguity Detector

基于意图与实体列表识别歧义与不确定项，并生成面向用户的澄清问题。仅负责识别与产出问题，不替用户做假设。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 理解层第三步，意图与实体已就绪，需决定是否可进入规划层
- 用户明确要求「歧义检测」「澄清问题生成」「检查有哪些不清楚的需要问用户」

**Do NOT use this Skill when:**
- 尚未有意图或实体（先完成 intent-parser、entity-extractor）
- 需要选模板、拆步骤或生成 BPMN（属规划层/建模层）
- 替用户做选择或默认填值（禁止）

## Instructions

1. **Check intent completeness** — 检查意图完整性：目标是否清晰？约束是否具体？
2. **Check entity coverage** — 检查实体覆盖：所有角色是否定义？系统边界是否清晰？
3. **Check trigger clarity** — 检查触发条件：流程何时启动？是否存在多触发？
4. **Generate clarification questions** — 为每个歧义点生成具体、可操作的澄清问题
5. **Set has_ambiguity** — 若无歧义，设置 `has_ambiguity: false`；否则为 `true`

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| intent | IntentOutput | intent-parser 输出 |
| entities | EntityOutput | entity-extractor 输出 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| has_ambiguity | boolean | 是否存在歧义 |
| ambiguity_points | AmbiguityPoint[] | 歧义点列表 |
| clarification_questions | string[] | 面向用户的澄清问题 |

**AmbiguityPoint 结构**：`{ type: string, description: string, affected_entities: string[] }`

## Example

**Input:**
```json
{
  "intent": {
    "business_type": "alert-handling",
    "goal": "处理告警",
    "constraints": [],
    "scope": ""
  },
  "entities": {
    "roles": [],
    "systems": [{ "id": "sys_1", "name": "告警系统", "description": "未明确" }],
    "data_objects": [],
    "triggers": []
  }
}
```

**Output:**
```json
{
  "has_ambiguity": true,
  "ambiguity_points": [
    {
      "type": "scope",
      "description": "未明确告警处理失败后的升级路径",
      "affected_entities": ["sys_1"]
    }
  ],
  "clarification_questions": [
    "告警自动恢复失败后，是否需要升级到运维团队？升级的触发条件是什么？"
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- 详细 I/O Schema：See `references/api-reference.md`

## Constraints

- 仅识别「缺失或矛盾」的信息，不扩大范围
- 问题需具体、可回答，避免笼统
- 有歧义时由编排层返回用户并等待，本 skill 不替用户做假设
