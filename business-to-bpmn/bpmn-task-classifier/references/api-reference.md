# BPMN Task Classifier · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| element_map | ElementMapping[] | 是 | bpmn-element-mapper 输出 |
| entities | EntityOutput | 是 | entity-extractor 输出（roles, systems, data_objects, triggers） |
| steps | Step[] | 是 | process-decomposer 输出（含 actor、description） |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| task_types | TaskTypeAssignment[] | 任务子类型分配列表 |

## TaskTypeAssignment 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| step_id | string | 对应步骤 id |
| bpmn_id | string | 对应 BPMN 元素 id |
| task_kind | string | "userTask" \| "serviceTask" \| "scriptTask" |
| reason | string | 分类决策理由 |

## 分类规则

- 人工角色（员工、主管、运维人员、审批者）→ userTask
- 系统/服务（系统、Agent、API、平台）→ serviceTask
- 脚本/计算/转换相关 → scriptTask
- 默认 → serviceTask

输出后由编排层交给 bpmn-model-assembler。
