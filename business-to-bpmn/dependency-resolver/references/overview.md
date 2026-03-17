# 依赖解析 · 能力概述

将步骤列表转化为 DAG（nodes + edges）。仅做依赖计算与图结构输出，不做并行优化、不修改节点。输出可交给 parallel-optimizer 或直接进入 BPMN 建模层。

**输入**：有序步骤列表（process-decomposer 输出）。**输出**：dag.nodes[]、dag.edges[]（from, to, condition?, type）。保证无环。详见 `api-reference.md`。
