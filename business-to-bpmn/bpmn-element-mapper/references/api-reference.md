# BPMN Element Mapper · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| steps | Step[] | 是 | process-decomposer 输出（含 id, name, type, bpmn_hint, preconditions） |
| dag | DAG | 是 | dependency-resolver 输出（nodes, edges） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| element_map | ElementMapping[] | BPMN 元素映射列表 |

## ElementMapping 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| step_id | string | 对应步骤 id |
| bpmn_type | string | "startEvent" \| "endEvent" \| "task" \| "exclusiveGateway" \| "parallelGateway" \| "intermediateCatchEvent" \| "intermediateThrowEvent" |
| bpmn_id | string | BPMN 元素 id（格式 Element_N） |
| name | string | 元素名称 |

## 映射规则

- 单出度起始节点 → startEvent
- 无后继终止节点 → endEvent
- 多条条件出边（互斥） → exclusiveGateway
- 多条无条件出边（并行） → parallelGateway
- 其他 action 节点 → task

输出后由编排层交给 bpmn-task-classifier 或 bpmn-model-assembler。
