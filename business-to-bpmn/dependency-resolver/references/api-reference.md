# Dependency Resolver · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| steps | Step[] | 是 | process-decomposer 输出（每步含 id, name, type, preconditions） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| dag | object | 含 nodes 与 edges |
| dag.nodes | string[] | 节点 id 列表 |
| dag.edges | Edge[] | 有向边列表 |

## Edge 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| from | string | 源节点 id |
| to | string | 目标节点 id |
| condition | string | 可选，决策分支条件描述 |
| type | string | "sequence" \| "conditional" \| "loop_back" |

仅根据 preconditions 解析出 from→to，保证无环。conditional 用于决策分支；loop_back 用于回环路径（如退回→重新提交）。输出后由编排层交给 parallel-optimizer 或 BPMN 建模层。
