---
name: bpmn-task-classifier
description: Determines task subtypes (userTask, serviceTask, scriptTask) for BPMN task elements based on entities and step context. Only classifies tasks, does not modify other elements. Use when task classification, 任务分类, task子类型, or assigning userTask/serviceTask/scriptTask.
bundle_scope: bpmn-agent
risk_level: L2
---

# BPMN Task Classifier

为 BPMN 中的 task 节点确定子类型：userTask、serviceTask 或 scriptTask。依据实体中的角色信息与步骤名称/描述进行启发式分类。仅做任务子类型决策，不修改其他 BPMN 元素。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 建模层，element_map 已就绪，需要为 task 分配子类型
- 用户明确要求「任务分类」「确定 task 子类型」「区分人工任务和服务任务」

**Do NOT use this Skill when:**
- 需要做节点到 BPMN 类型的首次映射（用 bpmn-element-mapper）
- 需要组装模型或输出 XML（用 bpmn-model-assembler）

## Instructions

1. **Filter tasks** — 仅处理 element_map 中 bpmn_type == "task" 的元素
2. **Look up step** — 根据 step_id 查找原始步骤的 actor 与描述
3. **Match entities** — 将 actor 与 entities.roles、entities.systems 匹配
4. **Apply heuristics** — 按分类规则决定 task_kind
5. **Record reason** — 为每个分类决策记录 reason 字段

## Classification Heuristics

| 条件 | task_kind | 说明 |
|------|-----------|------|
| actor 为人工角色（员工、主管、运维人员、审批者） | userTask | 需人工参与 |
| actor 为系统/服务（系统、Agent、API、平台、设备端） | serviceTask | 调用外部服务或自动化 |
| 步骤涉及脚本/计算/转换（含「脚本」「计算」「转换」等） | scriptTask | 执行脚本逻辑 |
| 默认 | serviceTask | 自动化流程中系统任务最常见 |

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| element_map | ElementMapping[] | bpmn-element-mapper 输出 |
| entities | EntityOutput | entity-extractor 输出（roles, systems, data_objects, triggers） |
| steps | Step[] | process-decomposer 输出（含 actor、description） |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| task_types | TaskTypeAssignment[] | 任务子类型分配列表 |

**TaskTypeAssignment**：`{ step_id: string, bpmn_id: string, task_kind: "userTask"|"serviceTask"|"scriptTask", reason: string }`

## Example

**Input:**
```json
{
  "element_map": [
    { "step_id": "s3", "bpmn_type": "task", "bpmn_id": "Element_3", "name": "告警分析" },
    { "step_id": "s6", "bpmn_type": "task", "bpmn_id": "Element_6", "name": "人工确认" }
  ],
  "entities": {
    "roles": [{ "id": "role_1", "name": "运维人员", "description": "人工确认与处理" }],
    "systems": [{ "id": "sys_1", "name": "云端Agent", "description": "云端多模态Agent平台" }]
  },
  "steps": [
    { "id": "s3", "name": "告警分析", "actor": "云端Agent", "description": "云端分析告警类型" },
    { "id": "s6", "name": "人工确认", "actor": "运维人员", "description": "高风险需人工确认" }
  ]
}
```

**Output:**
```json
{
  "task_types": [
    { "step_id": "s6", "bpmn_id": "Element_6", "task_kind": "userTask", "reason": "actor is 运维人员 (human role)" },
    { "step_id": "s3", "bpmn_id": "Element_3", "task_kind": "serviceTask", "reason": "actor is 云端Agent (system)" }
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅输出 task 的 task_kind，不修改 startEvent/endEvent/gateway
- 每个 task 必须有且仅有一个 task_kind
- 无 actor 或无法匹配时，默认 serviceTask
