# Process Decomposer · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| goal | string | 是 | 业务目标 |
| entities | EntityOutput | 是 | entity-extractor 输出（roles, systems, data_objects, triggers） |
| template_hint | TemplateCandidate | 否 | bpmn-template-matcher 候选，用于指导步骤结构 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| steps | Step[] | 有序步骤列表 |

## Step 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 步骤唯一标识（如 s1、s2） |
| name | string | 步骤名称 |
| type | string | "action" \| "decision" \| "event" \| "subprocess" |
| bpmn_hint | string | 建议的 BPMN 元素类型（userTask、serviceTask、exclusiveGateway、startEvent、endEvent 等） |
| preconditions | string[] | 前置步骤 id 列表 |
| description | string | 步骤描述 |
| actor | string | 执行主体（来自 roles 或 systems） |

至少包含一个 type: "event"、bpmn_hint: "startEvent" 的步骤和一个 type: "event"、bpmn_hint: "endEvent" 的步骤。输出后由编排层交给 dependency-resolver。
