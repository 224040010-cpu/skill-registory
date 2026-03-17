# BPMN XML Serializer · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| process | ProcessModel | 是 | 流程模型 |
| participants | Participant[] | 是 | 参与者（池）列表 |
| lanes | Lane[] | 是 | 泳道列表 |
| message_flows | MessageFlow[] | 是 | 跨参与者消息流列表 |

## ProcessModel 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 流程 id |
| name | string | 流程名称 |
| flowNodes | FlowNode[] | 流节点列表 |
| sequenceFlows | SequenceFlow[] | 序列流列表 |

## FlowNode 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 节点 id |
| type | string | startEvent、endEvent、userTask、serviceTask、scriptTask、exclusiveGateway、parallelGateway |
| name | string | 节点名称 |

## SequenceFlow 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 流 id |
| sourceRef | string | 源节点 id |
| targetRef | string | 目标节点 id |
| conditionExpression | string | 可选，条件表达式 |

## Participant 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 参与者 id |
| name | string | 参与者名称 |
| processRef | string | 引用 process id |

## Lane 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 泳道 id |
| name | string | 泳道名称 |
| participant_id | string | 所属参与者 id |
| flowNodeRefs | string[] | 该泳道内的 flowNode id 列表 |

## MessageFlow 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 消息流 id |
| sourceRef | string | 源节点 id |
| targetRef | string | 目标节点 id |
| name | string | 可选，消息流名称 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| bpmn_xml | string | 完整 BPMN 2.0 XML 字符串 |

输出后由编排层交给 bpmn-diagram-optimizer 或 bpmn-compliance-validator。
