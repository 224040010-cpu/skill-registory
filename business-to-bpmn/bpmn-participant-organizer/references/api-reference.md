# BPMN Participant Organizer · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| process | ProcessModel | 是 | bpmn-model-assembler 输出的流程模型 |
| entities | EntityOutput | 是 | entity-extractor 输出（roles, systems） |
| steps | Step[] | 否 | 用于获取 flowNode 与 actor 的映射 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| participants | Participant[] | 参与者（池）列表 |
| lanes | Lane[] | 泳道列表 |
| message_flows | MessageFlow[] | 跨参与者消息流列表 |

## Participant 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 参与者 id |
| name | string | 参与者名称 |
| processRef | string | 关联的 process id |

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
| name | string | 可选，消息流名称 |
| sourceRef | string | 源节点 id |
| targetRef | string | 目标节点 id |

输出后由编排层用于生成含 collaboration、laneSet、messageFlow 的 BPMN XML。
