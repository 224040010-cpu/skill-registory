---
name: bpmn-xml-serializer
description: Serializes BPMN process model (with participants, lanes, message flows) into BPMN 2.0 compliant XML string. Includes definitions root, process elements, collaboration, and basic BPMNDI diagram. Only does serialization, no validation or model modification. Use when BPMN XML serialization, XML生成, 序列化BPMN, or 导出XML.
bundle_scope: bpmn-agent
risk_level: L1
---

# BPMN XML Serializer

将 BPMN 流程模型（含参与者、泳道、消息流）序列化为符合 BPMN 2.0 的 XML 字符串（definitions 根、collaboration、process、BPMNDI），可在 bpmn.io 中直接打开。仅做序列化，不校验、不修改模型。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 渲染层，process、participants、lanes、message_flows 已就绪，需要输出 XML
- 用户明确要求「BPMN XML 序列化」「XML 生成」「序列化 BPMN」「导出 XML」

**Do NOT use this Skill when:**
- 需要校验 XML（用 bpmn-compliance-validator）
- 需要优化布局或美化（用 bpmn-diagram-optimizer）

## Instructions

1. **Create XML with proper namespaces:**
   - xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
   - xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
   - xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
   - xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
   - xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0"

2. **Build collaboration element** with participants

3. **For each participant**, build process element with flowNodes and sequenceFlows

4. **Build laneSet** within each process

5. **Add messageFlow elements** to collaboration

6. **Generate basic BPMNDI** with placeholder positions (layout optimizer will refine)

7. **BPMNShape positions:** start at (x=180, y=80), increment x by 180 for each node

8. **BPMNEdge waypoints:** simple straight lines between connected shapes

## XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" ...>
  <collaboration id="Collaboration_1">
    <participant id="..." name="..." processRef="..." />
    <messageFlow id="..." sourceRef="..." targetRef="..." />
  </collaboration>
  <process id="..." name="..." isExecutable="true">
    <laneSet id="...">
      <lane id="..." name="...">
        <flowNodeRef>...</flowNodeRef>
      </lane>
    </laneSet>
    <startEvent id="..." name="..." />
    <userTask id="..." name="..." />
    <serviceTask id="..." name="..." />
    <exclusiveGateway id="..." name="..." />
    <sequenceFlow id="..." sourceRef="..." targetRef="..." />
    <endEvent id="..." name="..." />
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_1">
      <bpmndi:BPMNShape ... />
      <bpmndi:BPMNEdge ... />
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>
```

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| process | ProcessModel | 流程模型（flowNodes、sequenceFlows） |
| participants | Participant[] | 参与者（池）列表 |
| lanes | Lane[] | 泳道列表 |
| message_flows | MessageFlow[] | 跨参与者消息流列表 |

**ProcessModel:** `{ id: string, name: string, flowNodes: FlowNode[], sequenceFlows: SequenceFlow[] }`

**Participant:** `{ id: string, name: string, processRef: string }`

**Lane:** `{ id: string, name: string, participant_id: string, flowNodeRefs: string[] }`

**MessageFlow:** `{ id: string, name?: string, sourceRef: string, targetRef: string }`

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| bpmn_xml | string | 完整 BPMN 2.0 XML 字符串 |

## Example

**Input:**
```json
{
  "process": {
    "id": "Process_1",
    "name": "告警处理流程",
    "flowNodes": [
      { "id": "Element_1", "type": "startEvent", "name": "开始" },
      { "id": "Element_2", "type": "serviceTask", "name": "告警检测" },
      { "id": "Element_3", "type": "userTask", "name": "人工确认" },
      { "id": "Element_4", "type": "exclusiveGateway", "name": "风险判断" },
      { "id": "Element_5", "type": "endEvent", "name": "结束" }
    ],
    "sequenceFlows": [
      { "id": "Flow_1", "sourceRef": "Element_1", "targetRef": "Element_2" },
      { "id": "Flow_2", "sourceRef": "Element_2", "targetRef": "Element_3" },
      { "id": "Flow_3", "sourceRef": "Element_3", "targetRef": "Element_4" },
      { "id": "Flow_4", "sourceRef": "Element_4", "targetRef": "Element_5" }
    ]
  },
  "participants": [
    { "id": "Participant_1", "name": "主流程", "processRef": "Process_1" }
  ],
  "lanes": [
    { "id": "Lane_1", "name": "系统", "participant_id": "Participant_1", "flowNodeRefs": ["Element_1", "Element_2", "Element_4"] },
    { "id": "Lane_2", "name": "运维", "participant_id": "Participant_1", "flowNodeRefs": ["Element_3", "Element_5"] }
  ],
  "message_flows": []
}
```

**Output:**
```json
{
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅做序列化，不校验 XML、不修改模型
- BPMNDI 为占位布局，后续由 bpmn-diagram-optimizer 优化
