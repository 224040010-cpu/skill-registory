# BPMN 元素映射 · 能力概述

将流程步骤与 DAG 映射为 BPMN 2.0 元素类型（startEvent、endEvent、task、exclusiveGateway、parallelGateway、intermediateCatchEvent、intermediateThrowEvent）。仅做类型映射，不决定 task 子类型、不生成 XML。输出由编排层交给 bpmn-task-classifier 或 bpmn-model-assembler。

**输入**：steps（process-decomposer 输出）、dag（dependency-resolver 输出）。**输出**：element_map[]（step_id、bpmn_type、bpmn_id、name）。详见 `api-reference.md`。
