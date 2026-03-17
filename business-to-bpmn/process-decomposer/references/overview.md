# 流程分解 · 能力概述

将业务目标与实体列表拆解为有序步骤，每步含 id、name、type、bpmn_hint、preconditions、actor。仅做步骤拆分与顺序规划，不计算 DAG、不生成节点配置。输出由编排层交给 dependency-resolver。

**输入**：goal、entities（entity-extractor 输出）、可选 template_hint。**输出**：steps[]。详见 `api-reference.md`。
