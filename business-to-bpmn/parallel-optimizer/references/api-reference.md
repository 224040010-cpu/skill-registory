# Parallel Optimizer · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| dag | DAG | 是 | dependency-resolver 输出（nodes, edges） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| execution_plan | object | 执行计划 |
| execution_plan.parallel_groups | string[][] | 可并行节点组，每组内节点拓扑层级相同 |
| execution_plan.sequential_order | string[] | 完整拓扑序（节点 id 列表） |

同一网关分支下的互斥节点（如 conditional 的不同分支）须分入不同组。仅当同层级且无互斥约束时，节点可归入同一 parallel_group。无并行机会时每组仅含一个节点。输出后由编排层交给 BPMN 建模层。
