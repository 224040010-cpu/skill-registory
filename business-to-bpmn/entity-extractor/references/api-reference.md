# Entity Extractor · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_description | string | 是 | 用户自然语言业务描述 |
| intent | IntentOutput | 是 | intent-parser 输出（business_type, goal, constraints, scope） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| roles | Entity[] | 参与角色（人、部门、系统作为执行主体） |
| systems | Entity[] | 涉及系统/服务/平台/设备 |
| data_objects | Entity[] | 数据对象（工单、报告、告警、订单等） |
| triggers | Entity[] | 触发条件（启动流程的事件） |

## Entity 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识（如 role_1、sys_1、data_1、trigger_1） |
| name | string | 实体名称 |
| description | string | 实体描述 |

同一实体只出现一次，命名一致。输出后由编排层决定下一步（通常为 ambiguity-detector）。
