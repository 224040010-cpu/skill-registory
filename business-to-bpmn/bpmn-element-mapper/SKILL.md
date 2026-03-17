---
name: bpmn-element-mapper
description: Maps process steps and DAG to BPMN 2.0 element types (startEvent, endEvent, task, exclusiveGateway, parallelGateway, intermediateEvent). Only does type mapping, does not determine task subtypes. Use when BPMN element mapping, 元素映射, BPMN类型分配, or assigning BPMN types from steps and DAG.
---

# BPMN Element Mapper

将流程步骤与 DAG 映射为 BPMN 2.0 元素类型（startEvent、endEvent、task、exclusiveGateway、parallelGateway、intermediateCatchEvent、intermediateThrowEvent）及 sequenceFlow 的 sourceRef/targetRef。仅做类型映射，不决定 task 子类型、不生成 XML。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 建模层，步骤与 DAG 已就绪，需要映射 BPMN 元素类型
- 用户明确要求「元素映射」「BPMN 类型分配」「将步骤转为 BPMN 元素」

**Do NOT use this Skill when:**
- 需要确定 task 子类型（userTask/serviceTask/scriptTask）（用 bpmn-task-classifier）
- 需要组装完整 BPMN 模型或生成 XML（用 bpmn-model-assembler）

## Instructions

1. **Map start event** — 单出度起始节点或 step type "event" 且 bpmn_hint "startEvent" → startEvent
2. **Map end event** — 无后继的终止节点或 step type "event" 且 bpmn_hint "endEvent" → endEvent
3. **Map decision** — step type "decision" → exclusiveGateway（默认）或 parallelGateway（若为并行分支）
4. **Map action** — step type "action" → task（子类型由 bpmn-task-classifier 决定）
5. **Map parallel groups** — 若 parallel-optimizer 标注了并行组，添加 parallelGateway 对（fork + join）
6. **Generate bpmn_id** — 使用格式 "Element_" + 顺序号（如 Element_1、Element_2）

## Mapping Rules

| 条件 | BPMN 类型 |
|------|-----------|
| 单出度起始节点 | startEvent |
| 无后继的终止节点 | endEvent |
| 多条条件出边（互斥分支） | exclusiveGateway |
| 多条无条件出边（并行分支） | parallelGateway |
| 其他 action 节点 | task |

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| steps | Step[] | process-decomposer 输出的有序步骤 |
| dag | DAG | dependency-resolver 输出的依赖图 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| element_map | ElementMapping[] | BPMN 元素映射列表 |

**ElementMapping**：`{ step_id: string, bpmn_type: "startEvent"|"endEvent"|"task"|"exclusiveGateway"|"parallelGateway"|"intermediateCatchEvent"|"intermediateThrowEvent", bpmn_id: string, name: string }`

## Example

**Input:**
```json
{
  "steps": [
    { "id": "s1", "name": "告警触发", "type": "event", "bpmn_hint": "startEvent", "preconditions": [] },
    { "id": "s4", "name": "风险级别判断", "type": "decision", "bpmn_hint": "exclusiveGateway", "preconditions": ["s3"] },
    { "id": "s10", "name": "流程结束", "type": "event", "bpmn_hint": "endEvent", "preconditions": ["s9"] }
  ],
  "dag": {
    "nodes": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"],
    "edges": [
      { "from": "s1", "to": "s2", "type": "sequence" },
      { "from": "s4", "to": "s5", "type": "conditional", "condition": "低风险" },
      { "from": "s4", "to": "s6", "type": "conditional", "condition": "高风险" },
      { "from": "s9", "to": "s10", "type": "sequence" }
    ]
  }
}
```

**Output:**
```json
{
  "element_map": [
    { "step_id": "s1", "bpmn_type": "startEvent", "bpmn_id": "Element_1", "name": "告警触发" },
    { "step_id": "s2", "bpmn_type": "task", "bpmn_id": "Element_2", "name": "告警上报" },
    { "step_id": "s3", "bpmn_type": "task", "bpmn_id": "Element_3", "name": "告警分析" },
    { "step_id": "s4", "bpmn_type": "exclusiveGateway", "bpmn_id": "Element_4", "name": "风险级别判断" },
    { "step_id": "s5", "bpmn_type": "task", "bpmn_id": "Element_5", "name": "自动恢复" },
    { "step_id": "s6", "bpmn_type": "task", "bpmn_id": "Element_6", "name": "人工确认" },
    { "step_id": "s7", "bpmn_type": "task", "bpmn_id": "Element_7", "name": "执行恢复命令" },
    { "step_id": "s8", "bpmn_type": "task", "bpmn_id": "Element_8", "name": "结果验证" },
    { "step_id": "s9", "bpmn_type": "task", "bpmn_id": "Element_9", "name": "生成报告" },
    { "step_id": "s10", "bpmn_type": "endEvent", "bpmn_id": "Element_10", "name": "流程结束" }
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅输出类型映射，不决定 task 子类型
- bpmn_id 按步骤顺序递增，保证唯一
- 不生成 XML 或 process 结构
