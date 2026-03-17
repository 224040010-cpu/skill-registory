---
name: parallel-optimizer
description: Analyzes DAG for parallel execution feasibility, outputs execution plan with parallel groups. Only does topological analysis, does not change dependencies. Use when parallel optimization, 并行优化, 并行分析, or analyzing parallel execution in business-to-bpmn planning layer.
bundle_scope: bpmn-agent
risk_level: L2
---

# Parallel Optimizer

对 DAG 进行并行可行性分析，输出标注了可并行节点的执行计划。仅做并行分析，不修改依赖关系或节点定义。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 规划层，DAG 已就绪，需要可并行标注
- 用户明确要求「并行优化」「并行分析」「标注可并行节点」

**Do NOT use this Skill when:**
- 需要映射 BPMN 元素或生成 XML（用 bpmn-element-mapper、bpmn-model-assembler）
- 需要修改依赖或步骤（用 dependency-resolver、process-decomposer）

## Instructions

1. **Topological sort** — 对 DAG 执行拓扑排序，得到执行顺序
2. **Group by level** — 将同一拓扑层级的节点归为一组（无依赖关系，可并行执行）
3. **Apply mutual exclusion** — 同一网关分支下的节点互斥，不可并行（如 s5 与 s6 来自 s4 的不同分支，不能同组）
4. **Output execution_plan** — parallel_groups：每组为可并行节点 id 列表；sequential_order：完整拓扑序

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| dag | DAG | dependency-resolver 输出（nodes, edges） |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| execution_plan | object | 执行计划 |
| execution_plan.parallel_groups | string[][] | 可并行节点组，每组内节点可同时执行 |
| execution_plan.sequential_order | string[] | 完整拓扑序（节点 id 列表） |

## Example

**Input:**
```json
{
  "dag": {
    "nodes": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"],
    "edges": [
      { "from": "s1", "to": "s2", "type": "sequence" },
      { "from": "s2", "to": "s3", "type": "sequence" },
      { "from": "s3", "to": "s4", "type": "sequence" },
      { "from": "s4", "to": "s5", "type": "conditional", "condition": "低风险" },
      { "from": "s4", "to": "s6", "type": "conditional", "condition": "高风险" },
      { "from": "s6", "to": "s7", "type": "sequence" },
      { "from": "s5", "to": "s8", "type": "sequence" },
      { "from": "s7", "to": "s8", "type": "sequence" },
      { "from": "s8", "to": "s9", "type": "sequence" },
      { "from": "s9", "to": "s10", "type": "sequence" }
    ]
  }
}
```

**Output:**
```json
{
  "execution_plan": {
    "parallel_groups": [
      ["s1"],
      ["s2"],
      ["s3"],
      ["s4"],
      ["s5"],
      ["s6"],
      ["s7"],
      ["s8"],
      ["s9"],
      ["s10"]
    ],
    "sequential_order": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"]
  }
}
```

**Note:** s5 与 s6 来自同一网关 s4 的不同分支，互斥执行，故分入不同 parallel_group。仅当同层级且无互斥约束时，节点可归入同一组。

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅基于 DAG 拓扑分析，不引入业务假设
- 不修改 dag 的 nodes 或 edges
- 无并行机会时 parallel_groups 中每组仅含一个节点
