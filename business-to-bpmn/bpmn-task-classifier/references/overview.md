# BPMN 任务分类 · 能力概述

为 BPMN 中的 task 节点确定子类型：userTask、serviceTask 或 scriptTask。依据实体中的角色与系统信息及步骤的 actor 进行启发式分类。仅做任务子类型决策，不修改其他 BPMN 元素。输出由编排层交给 bpmn-model-assembler。

**输入**：element_map、entities、steps。**输出**：task_types[]（step_id、bpmn_id、task_kind、reason）。详见 `api-reference.md`。
