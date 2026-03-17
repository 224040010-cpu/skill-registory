# Entity Extractor · 能力概述

从用户描述与结构化意图中抽取关键实体（角色、系统、数据对象、触发条件），供歧义检测与 BPMN 建模使用。

**职责边界**：仅做实体识别与列举，不做实体间关联推理、不排顺序、不生成步骤或 BPMN。

**输入**：`{ user_description: string, intent: IntentOutput }` — 用户描述 + intent-parser 输出。

**输出**：`{ roles, systems, data_objects, triggers }` — 按类型分组的 Entity 数组。详见 `api-reference.md`。

**Entity 结构**：每个实体含 `id`、`name`、`description`，ID 格式为 `role_1`、`sys_1`、`data_1`、`trigger_1` 等。
