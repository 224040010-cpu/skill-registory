# BPMN 参与者组织 · 能力概述

将 BPMN 模型中的 flowNode 分配到不同泳道（Lane）和参与者（Participant/Pool），并在不同参与者之间创建 messageFlow。仅做参与者组织与分配，不修改流程逻辑。输出由编排层用于生成含 collaboration、laneSet、messageFlow 的 BPMN XML。

**输入**：process、entities、可选 steps。**输出**：participants[]、lanes[]、message_flows[]。详见 `api-reference.md`。
