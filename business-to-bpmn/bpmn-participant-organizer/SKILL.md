---
name: bpmn-participant-organizer
description: Assigns process flow nodes to participants (pools) and lanes based on entity roles and systems. Creates message flows between different participants. Only handles participant organization, does not modify process logic. Use when swimlane assignment, 泳道分配, participant organization, 参与者组织, or organizing BPMN by pools and lanes.
---

# BPMN Participant Organizer

将 BPMN 模型中的 flowNode 分配到不同泳道（Lane）和参与者（Participant/Pool），并在不同参与者之间创建 messageFlow。仅做参与者组织与分配，不修改流程逻辑。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 建模层，process 已就绪，需要按参与者/泳道组织
- 用户明确要求「泳道分配」「参与者组织」「按角色分池」「创建 messageFlow」

**Do NOT use this Skill when:**
- 需要组装 process 模型（用 bpmn-model-assembler）
- 需要序列化 XML（由编排层调用 emitting-bpmn-xml）

## Instructions

1. **Group entities** — 按类型分组：人工角色 → 一个池或泳道，系统 → 独立池或池内泳道
2. **Strategy decision** — 若所有 actor 属于同一组织 → 单池多泳道；若跨组织/系统 → 多池 + messageFlow
3. **Assign flowNodes** — 根据步骤的 actor 将每个 flowNode 分配到对应 lane
4. **Create messageFlows** — 跨池交互时，创建 messageFlow 元素
5. **Default lane** — 无 actor 的节点分配到「System」默认泳道

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| process | ProcessModel | bpmn-model-assembler 输出的流程模型 |
| entities | EntityOutput | entity-extractor 输出（roles, systems） |
| steps | Step[] | 可选，用于获取 flowNode 与 actor 的映射 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| participants | Participant[] | 参与者（池）列表 |
| lanes | Lane[] | 泳道列表 |
| message_flows | MessageFlow[] | 跨参与者消息流列表 |

**Participant**：`{ id: string, name: string, processRef: string }`

**Lane**：`{ id: string, name: string, participant_id: string, flowNodeRefs: string[] }`

**MessageFlow**：`{ id: string, name?: string, sourceRef: string, targetRef: string }`

## Example

**Input:**
```json
{
  "process": {
    "id": "Process_ChargingPileAlert",
    "name": "充电桩告警自动诊断与分级恢复",
    "flowNodes": [
      { "id": "Element_1", "type": "startEvent", "name": "告警触发" },
      { "id": "Element_2", "type": "serviceTask", "name": "告警上报" },
      { "id": "Element_3", "type": "serviceTask", "name": "告警分析" },
      { "id": "Element_6", "type": "userTask", "name": "人工确认" }
    ],
    "sequenceFlows": []
  },
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
  "participants": [
    { "id": "Participant_Device", "name": "设备端", "processRef": "Process_Device" },
    { "id": "Participant_Cloud", "name": "云端Agent平台", "processRef": "Process_Cloud" }
  ],
  "lanes": [
    { "id": "Lane_Device", "name": "设备端", "participant_id": "Participant_Device", "flowNodeRefs": ["Element_1", "Element_2"] },
    { "id": "Lane_Cloud", "name": "云端Agent", "participant_id": "Participant_Cloud", "flowNodeRefs": ["Element_3", "Element_4", "Element_5"] },
    { "id": "Lane_Ops", "name": "运维人员", "participant_id": "Participant_Cloud", "flowNodeRefs": ["Element_6"] }
  ],
  "message_flows": [
    { "id": "MessageFlow_1", "name": "告警上报", "sourceRef": "Element_2", "targetRef": "Element_3" }
  ]
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 不修改 process 中的 flowNodes 或 sequenceFlows
- 每个 flowNode 仅属于一个 lane
- messageFlow 的 sourceRef/targetRef 引用 flowNode id 或消息事件 id
