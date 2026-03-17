# BPMN 模型组装 · 能力概述

根据 BPMN 元素映射、任务类型与 DAG 构建 BPMN 流程的内存模型。process 含 flowNodes、sequenceFlows，含 id、name、sourceRef、targetRef、conditionExpression。仅做模型组装，不处理泳道/池、不序列化 XML。输出由编排层交给 bpmn-participant-organizer 或 XML 序列化层。

**输入**：element_map、task_types、dag、可选 process_id/process_name。**输出**：process（id、name、flowNodes[]、sequenceFlows[]）。详见 `api-reference.md`。
