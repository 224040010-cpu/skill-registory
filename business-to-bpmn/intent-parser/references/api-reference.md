# Intent Parser · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_description | string | 是 | 用户自然语言业务描述（一段或多段文本） |

## 输出

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| business_type | string | 是 | 业务类型（如 approval、data-sync、alert-handling、reporting） |
| goal | string | 是 | 用户期望达成的流程目标 |
| constraints | string[] | 是 | 约束条件列表（时限、审批层级、重试策略等） |
| scope | string | 否 | 范围说明（涉及的系统、部门、设备） |

## 输出后行为

不调用其他 skill；由 business-to-bpmn 编排层决定下一步（通常为 entity-extractor）。
