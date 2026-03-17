---
name: dependency-resolver
description: Computes dependency relationships from step list, outputs DAG (nodes + directed edges). Only does dependency calculation, no optimization. Use when dependency resolution, 依赖计算, DAG生成, or building DAG from steps in business-to-bpmn planning layer.
bundle_scope: bpmn-agent
risk_level: L1
---

# Dependency Resolver

根据步骤列表计算依赖关系，输出 DAG（节点与有向边）。仅做依赖计算与图结构输出，不做流程优化或并行分析。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 规划层，步骤列表已就绪，需要得到依赖图
- 用户明确要求「依赖计算」「生成 DAG」「输出节点和边」

**Do NOT use this Skill when:**
- 需要标注可并行节点（用 parallel-optimizer）
- 需要映射 BPMN 元素或生成 XML（用 bpmn-element-mapper、bpmn-model-assembler）

## Instructions

1. **Create nodes** — 为每个 step 创建一个节点（使用 step.id）
2. **Parse preconditions** — 对每个 step 的 preconditions，创建边：from=precondition_id, to=step.id
3. **Handle decision steps** — 对 type: "decision" 的步骤，创建 conditional 边到各分支目标
4. **Detect loop_back** — 识别回环边（如 rejection → resubmit），标注 type: "loop_back"
5. **Validate** — 确保从 start 节点可达所有节点，无孤立节点

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| steps | Step[] | process-decomposer 输出的有序步骤列表 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| dag | object | 含 nodes 与 edges |
| dag.nodes | string[] | 节点 id 列表（对应 step.id） |
| dag.edges | Edge[] | 有向边列表 |

**Edge**：`{ from: string, to: string, condition?: string, type: "sequence"|"conditional"|"loop_back" }`

- **sequence**：普通顺序流
- **conditional**：决策分支，condition 描述分支条件
- **loop_back**：回环路径（如退回→重新提交）

## Example

**Input:**
```json
{
  "steps": [
    { "id": "s1", "name": "告警触发", "type": "event", "preconditions": [] },
    { "id": "s2", "name": "告警上报", "type": "action", "preconditions": ["s1"] },
    { "id": "s3", "name": "告警分析", "type": "action", "preconditions": ["s2"] },
    { "id": "s4", "name": "风险级别判断", "type": "decision", "preconditions": ["s3"] },
    { "id": "s5", "name": "自动恢复", "type": "action", "preconditions": ["s4"] },
    { "id": "s6", "name": "人工确认", "type": "action", "preconditions": ["s4"] },
    { "id": "s7", "name": "执行恢复命令", "type": "action", "preconditions": ["s6"] },
    { "id": "s8", "name": "结果验证", "type": "action", "preconditions": ["s5", "s7"] },
    { "id": "s9", "name": "生成报告", "type": "action", "preconditions": ["s8"] },
    { "id": "s10", "name": "流程结束", "type": "event", "preconditions": ["s9"] }
  ]
}
```

**Output:**
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

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅基于 preconditions 解析，保证无环
- 不标注可并行节点；不修改节点定义
