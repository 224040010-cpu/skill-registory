---
name: process-decomposer
description: Decomposes business goal and entity list into ordered process steps with BPMN element hints. Only does step splitting and ordering, not implementation details. Use when step decomposition, 步骤拆解, 流程分解, or converting goal+entities to ordered steps in business-to-bpmn planning layer.
bundle_scope: bpmn-agent
risk_level: L2
---

# Process Decomposer

将业务目标与实体列表拆解为有序的步骤列表，每步含名称、类型、BPMN 元素提示和前置依赖说明。仅做步骤拆分与顺序规划，不关心具体实现或节点配置。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 规划层，未命中高相似度模板，需要从 goal + entities 得到步骤列表
- 用户明确要求「步骤拆解」「流程分解」「把流程拆成步骤」

**Do NOT use this Skill when:**
- 需要计算依赖图或并行优化（用 dependency-resolver、parallel-optimizer）
- 需要映射 BPMN 元素或生成 XML（用 bpmn-element-mapper、bpmn-model-assembler）

## Instructions

1. **Start with trigger event** — 第一步为 type: "event", bpmn_hint: "startEvent"
2. **Order main actions** — 按业务逻辑排列：触发 → 主动作 → 决策点 → 结束事件
3. **Determine type and bpmn_hint** — 每步确定 type（action|decision|event|subprocess）并建议 bpmn_hint（userTask、serviceTask、exclusiveGateway、startEvent、endEvent 等）
4. **Assign actor** — 从 entity 列表（roles、systems）中分配执行主体
5. **List preconditions** — 列出前置步骤 id，明确依赖
6. **Ensure start and end** — 至少一个 start（type: "event", bpmn_hint: "startEvent"）和一个 end（type: "event", bpmn_hint: "endEvent"）

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| goal | string | 业务目标 |
| entities | EntityOutput | entity-extractor 输出（roles, systems, data_objects, triggers） |
| template_hint | TemplateCandidate | 可选，bpmn-template-matcher 的候选，用于指导步骤结构 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| steps | Step[] | 有序步骤列表 |

**Step**：`{ id: string, name: string, type: "action"|"decision"|"event"|"subprocess", bpmn_hint: string, preconditions: string[], description: string, actor: string }`

- **bpmn_hint**：建议的 BPMN 元素类型，如 userTask、serviceTask、exclusiveGateway、startEvent、endEvent

## Example

**Input:**
```json
{
  "goal": "充电桩告警自动诊断与分级恢复",
  "entities": {
    "roles": [{ "id": "role_1", "name": "运维人员", "description": "人工确认与处理" }],
    "systems": [
      { "id": "sys_1", "name": "设备端", "description": "充电桩设备" },
      { "id": "sys_2", "name": "云端Agent", "description": "云端多模态Agent平台" }
    ]
  }
}
```

**Output:**
```json
{
  "steps": [
    { "id": "s1", "name": "告警触发", "type": "event", "bpmn_hint": "startEvent", "preconditions": [], "description": "设备检测到异常", "actor": "设备端" },
    { "id": "s2", "name": "告警上报", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s1"], "description": "设备端上报告警", "actor": "设备端" },
    { "id": "s3", "name": "告警分析", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s2"], "description": "云端分析告警类型", "actor": "云端Agent" },
    { "id": "s4", "name": "风险级别判断", "type": "decision", "bpmn_hint": "exclusiveGateway", "preconditions": ["s3"], "description": "低风险/高风险分支", "actor": "云端Agent" },
    { "id": "s5", "name": "自动恢复", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s4"], "description": "低风险自动执行恢复", "actor": "云端Agent" },
    { "id": "s6", "name": "人工确认", "type": "action", "bpmn_hint": "userTask", "preconditions": ["s4"], "description": "高风险需人工确认", "actor": "运维人员" },
    { "id": "s7", "name": "执行恢复命令", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s6"], "description": "人工确认后执行", "actor": "云端Agent" },
    { "id": "s8", "name": "结果验证", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s5", "s7"], "description": "验证恢复结果", "actor": "云端Agent" },
    { "id": "s9", "name": "生成报告", "type": "action", "bpmn_hint": "serviceTask", "preconditions": ["s8"], "description": "生成处理报告", "actor": "云端Agent" },
    { "id": "s10", "name": "流程结束", "type": "event", "bpmn_hint": "endEvent", "preconditions": ["s9"], "description": "流程结束", "actor": "" }
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 依赖仅用 preconditions 描述，不在此生成有向图
- 不涉及执行器、参数、schema；bpmn_hint 仅为建模层提供参考
