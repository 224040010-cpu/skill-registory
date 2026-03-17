# Intent Coverage Evaluator · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bpmn_xml | string | 是 | BPMN 2.0 XML 字符串 |
| original_intent | IntentOutput | 是 | intent-parser 输出 |
| original_entities | EntityOutput | 是 | entity-extractor 输出 |

## IntentOutput 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| business_type | string | 业务类型 |
| goal | string | 流程目标 |
| constraints | string[] | 约束条件列表 |
| scope | string | 可选，范围说明 |

## EntityOutput 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| roles | Entity[] | 参与角色 |
| systems | Entity[] | 涉及系统 |
| data_objects | Entity[] | 数据对象 |
| triggers | Entity[] | 触发条件 |

## Entity 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识 |
| name | string | 实体名称 |
| description | string | 实体描述 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| coverage_score | number | 覆盖度评分（0–1） |
| covered_items | string[] | 已覆盖项列表 |
| missing_items | string[] | 缺失项列表 |
| recommendations | string[] | 改进建议列表 |

## 覆盖度计算

coverage_score = covered_items.length / (covered_items.length + missing_items.length)

输出后由编排层根据 coverage_score 决定是否交付或补充建模。
