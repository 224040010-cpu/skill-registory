---
name: bpmn-diagram-optimizer
description: Optimizes BPMN diagram layout, applies visual styling, and resolves label overlaps. Combines layout, styling, and label optimization into a single pass. Only modifies BPMNDI coordinates and visual attributes, does not change process logic. Use when diagram optimization, 布局优化, 视觉美化, 标签重叠, or BPMN美化.
---

# BPMN Diagram Optimizer

优化 BPMN 工作流的 BPMNDI 布局（正交布线、合理间距）、应用视觉美化（按泳道/类型着色）、解决标签重叠。合并布局+样式+标签三步为单次优化。仅修改 BPMNDI 层面属性，不修改流程逻辑。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 渲染层，BPMN XML 已生成，需要优化布局与视觉
- 用户明确要求「布局优化」「视觉美化」「标签重叠」「BPMN 美化」

**Do NOT use this Skill when:**
- 需要序列化模型为 XML（用 bpmn-xml-serializer）
- 需要校验 XML（用 bpmn-compliance-validator）

## Instructions

### Phase 1 — Layout

1. Parse existing BPMNDI shapes and edges
2. Apply left-to-right flow direction
3. Position elements with 180px horizontal spacing, 100px vertical spacing between lanes
4. Route edges using orthogonal paths (only horizontal/vertical segments)
5. Avoid edge-shape overlaps by routing around obstacles
6. Loop-back edges route below the main flow

### Phase 2 — Styling

1. Apply bioc:stroke and bioc:fill colors by element type:
   - startEvent: green (#52B415 stroke, #E8F5E9 fill)
   - endEvent: red (#E53935 stroke, #FFEBEE fill)
   - userTask: blue (#1E88E5 stroke, #E3F2FD fill)
   - serviceTask: orange (#FB8C00 stroke, #FFF3E0 fill)
   - scriptTask: purple (#8E24AA stroke, #F3E5F5 fill)
   - gateway: yellow (#FDD835 stroke, #FFFDE7 fill)
2. Lane backgrounds: alternate between light gray shades

### Phase 3 — Labels

1. Check for label-shape and label-label overlaps
2. Reposition labels to avoid overlaps (prefer below for events, right for gateways)
3. Shorten long names if needed (max 30 chars, add "..." suffix)

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| bpmn_xml | string | BPMN 2.0 XML 字符串 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| optimized_xml | string | 优化后的 BPMN XML 字符串 |
| layout_stats | LayoutStats | 优化统计信息 |

**LayoutStats:** `{ nodes_positioned: number, edges_routed: number, labels_resolved: number }`

## Example

**Input:**
```json
{
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

**Output:**
```json
{
  "optimized_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "layout_stats": {
    "nodes_positioned": 12,
    "edges_routed": 14,
    "labels_resolved": 3
  }
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅修改 BPMNDI 坐标与视觉属性，不修改 process、flowNodes、sequenceFlows
- 保持 BPMN 2.0 命名空间与结构合规
