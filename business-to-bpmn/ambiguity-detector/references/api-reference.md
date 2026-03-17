# Ambiguity Detector · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| intent | IntentOutput | 是 | intent-parser 输出（business_type, goal, constraints, scope） |
| entities | EntityOutput | 是 | entity-extractor 输出（roles, systems, data_objects, triggers） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| has_ambiguity | boolean | 是否存在歧义；无歧义时为 false |
| ambiguity_points | AmbiguityPoint[] | 歧义点列表；无歧义时为 [] |
| clarification_questions | string[] | 面向用户的澄清问题，可直接展示；无歧义时为 [] |

## AmbiguityPoint 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 歧义类型（如 scope、trigger、role、constraint） |
| description | string | 歧义描述 |
| affected_entities | string[] | 受影响的实体 ID 列表 |

无歧义时 `has_ambiguity: false`，`ambiguity_points` 与 `clarification_questions` 均为空。有歧义时由编排层将 `clarification_questions` 返回用户，不进入规划层。
