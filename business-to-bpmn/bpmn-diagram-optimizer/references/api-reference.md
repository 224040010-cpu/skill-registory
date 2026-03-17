# BPMN Diagram Optimizer · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bpmn_xml | string | 是 | BPMN 2.0 XML 字符串 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| optimized_xml | string | 优化后的 BPMN XML 字符串 |
| layout_stats | LayoutStats | 优化统计信息 |

## LayoutStats 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| nodes_positioned | number | 已定位的节点数量 |
| edges_routed | number | 已布线的边数量 |
| labels_resolved | number | 已解决重叠的标签数量 |

## 优化规则摘要

- **布局**：左到右流向，水平间距 180px，泳道间垂直间距 100px，正交布线
- **样式**：startEvent 绿、endEvent 红、userTask 蓝、serviceTask 橙、scriptTask 紫、gateway 黄
- **标签**：最大 30 字符，重叠时重定位（事件标签偏下、网关标签偏右）

输出后由编排层交付用户或交给 bpmn-compliance-validator 校验。
