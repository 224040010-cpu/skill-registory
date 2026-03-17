# BPMN Model Assembler · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| element_map | ElementMapping[] | 是 | bpmn-element-mapper 输出 |
| task_types | TaskTypeAssignment[] | 是 | bpmn-task-classifier 输出 |
| dag | DAG | 是 | dependency-resolver 输出 |
| process_id | string | 否 | process 的 id |
| process_name | string | 否 | process 的 name |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| process | ProcessModel | 完整 BPMN 流程的内存模型 |

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
| id | string | 节点 id（来自 element_map.bpmn_id） |
| type | string | startEvent、endEvent、userTask、serviceTask、scriptTask、exclusiveGateway、parallelGateway |
| name | string | 节点名称 |

## SequenceFlow 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 流 id（格式 Flow_N） |
| name | string | 可选，流名称 |
| sourceRef | string | 源节点 id |
| targetRef | string | 目标节点 id |
| conditionExpression | string | 可选，条件表达式 |

输出后由编排层交给 bpmn-participant-organizer 或 XML 序列化层。
