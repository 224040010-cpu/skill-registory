# 并行优化 · 能力概述

分析 DAG，找出无依赖关系的节点并标注为可并行。不修改 edges、不合并节点。输出由编排层交给 BPMN 建模层。

**输入**：DAG（dependency-resolver 输出）。**输出**：execution_plan（parallel_groups、sequential_order）。详见 `api-reference.md`。
