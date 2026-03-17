# BPMN XML Serializer · 能力概述

将 BPMN 流程模型（含参与者、泳道、消息流）序列化为符合 BPMN 2.0 的 XML 字符串。输出包含 definitions 根、collaboration、process、laneSet、messageFlow 及基础 BPMNDI 图形信息，可在 bpmn.io 或 Camunda 中直接打开。

**输入**：process、participants、lanes、message_flows。**输出**：bpmn_xml（完整 XML 字符串）。详见 `api-reference.md`。

仅做序列化，不校验、不修改模型。BPMNDI 使用占位坐标，后续由 bpmn-diagram-optimizer 进行布局优化与视觉美化。
