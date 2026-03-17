# BPMN Template Matcher · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| intent | IntentOutput | 是 | intent-parser 输出（business_type, goal, constraints, scope） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| candidates | TemplateCandidate[] | 候选模板列表，最多 3 个，按 similarity_score 降序 |
| best_match | object \| null | 最高分 ≥ 0.8 时非空；无 ≥ 0.5 时为 null |

## TemplateCandidate 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| template_id | string | 模板唯一标识 |
| template_name | string | 模板名称 |
| similarity_score | number | 相似度 [0, 1] |
| description | string | 模板描述 |

## best_match 结构（非 null 时）

| 字段 | 类型 | 说明 |
|------|------|------|
| template_id | string | 命中模板 ID |
| similarity_score | number | 相似度 |

相似度基于 goal 与 business_type 为主，constraints 与 scope 为辅。输出后由编排层决定下一步。
