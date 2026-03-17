---
name: bpmn-model-assembler
description: Assembles complete BPMN process model from element mappings, task types, and DAG. Creates flowNodes and sequenceFlows with IDs, names, sourceRef, targetRef, and conditionExpressions. Only does model assembly, does not handle lanes or serialization. Use when BPMN model assembly, 模型组装, 构建BPMN模型, or building process from element map.
bundle_scope: bpmn-agent
risk_level: L2
---

# BPMN Model Assembler

根据 BPMN 元素映射与 sequenceFlow 规格构建 BPMN 流程的内存模型（process 含 flowNodes、sequenceFlows，含 id、name、sourceRef、targetRef、conditionExpression）。仅做模型组装，不处理泳道/池、不序列化 XML。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 建模层，element_map、task_types、dag 已就绪，需要组装完整 process
- 用户明确要求「模型组装」「构建 BPMN 模型」「组装 process 与 sequenceFlow」

**Do NOT use this Skill when:**
- 需要分配泳道或参与者（用 bpmn-participant-organizer）
- 需要输出 XML（由编排层调用 emitting-bpmn-xml 等）

## Instructions

1. **Create flowNodes** — 从 element_map 创建 flowNodes，对 task 应用 task_types 中的 task_kind
2. **Create sequenceFlows** — 从 DAG edges 创建 sequenceFlows，使用 bpmn_id 作为 sourceRef/targetRef
3. **Add conditionExpression** — 对来自 exclusiveGateway 的条件边，添加 conditionExpression
4. **Handle parallelGateway** — 对 parallelGateway 对，确保 fork 与 join 正确连接
5. **Generate IDs** — sequenceFlow id 格式：`Flow_` + 顺序号（如 Flow_1、Flow_2）
6. **Set process** — 从 intent 或上下文设置 process.id、process.name

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| element_map | ElementMapping[] | bpmn-element-mapper 输出 |
| task_types | TaskTypeAssignment[] | bpmn-task-classifier 输出 |
| dag | DAG | dependency-resolver 输出 |
| process_id | string | 可选，process 的 id |
| process_name | string | 可选，process 的 name |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| process | ProcessModel | 完整 BPMN 流程的内存模型 |

**ProcessModel**：`{ id: string, name: string, flowNodes: FlowNode[], sequenceFlows: SequenceFlow[] }`

**FlowNode**：`{ id: string, type: string, name: string }`（type 为 startEvent、endEvent、userTask、serviceTask、scriptTask、exclusiveGateway、parallelGateway 等）

**SequenceFlow**：`{ id: string, name?: string, sourceRef: string, targetRef: string, conditionExpression?: string }`

## Example

**Input:**
```json
{
  "element_map": [
    { "step_id": "s1", "bpmn_type": "startEvent", "bpmn_id": "Element_1", "name": "告警触发" },
    { "step_id": "s4", "bpmn_type": "exclusiveGateway", "bpmn_id": "Element_4", "name": "风险级别判断" },
    { "step_id": "s10", "bpmn_type": "endEvent", "bpmn_id": "Element_10", "name": "流程结束" }
  ],
  "task_types": [
    { "step_id": "s6", "bpmn_id": "Element_6", "task_kind": "userTask", "reason": "actor is 运维人员" }
  ],
  "dag": {
    "nodes": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"],
    "edges": [
      { "from": "s1", "to": "s2", "type": "sequence" },
      { "from": "s4", "to": "s5", "type": "conditional", "condition": "低风险" },
      { "from": "s4", "to": "s6", "type": "conditional", "condition": "高风险" },
      { "from": "s9", "to": "s10", "type": "sequence" }
    ]
  },
  "process_id": "Process_ChargingPileAlert",
  "process_name": "充电桩告警自动诊断与分级恢复"
}
```

**Output:**
```json
{
  "process": {
    "id": "Process_ChargingPileAlert",
    "name": "充电桩告警自动诊断与分级恢复",
    "flowNodes": [
      { "id": "Element_1", "type": "startEvent", "name": "告警触发" },
      { "id": "Element_2", "type": "serviceTask", "name": "告警上报" },
      { "id": "Element_4", "type": "exclusiveGateway", "name": "风险级别判断" },
      { "id": "Element_6", "type": "userTask", "name": "人工确认" },
      { "id": "Element_10", "type": "endEvent", "name": "流程结束" }
    ],
    "sequenceFlows": [
      { "id": "Flow_1", "sourceRef": "Element_1", "targetRef": "Element_2" },
      { "id": "Flow_2", "sourceRef": "Element_4", "targetRef": "Element_5", "conditionExpression": "低风险" },
      { "id": "Flow_3", "sourceRef": "Element_4", "targetRef": "Element_6", "conditionExpression": "高风险" },
      { "id": "Flow_4", "sourceRef": "Element_9", "targetRef": "Element_10" }
    ]
  }
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅做内存模型组装，不处理泳道、不序列化 XML
- sourceRef/targetRef 必须引用 flowNode.id
- 无 task_types 的 task 默认 serviceTask
