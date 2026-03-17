# Intent Coverage Evaluator · 能力概述

评估 BPMN 工作流对原始用户意图的覆盖度。将 BPMN 中的任务、事件、网关条件与 intent-parser 输出的 goal、constraints 以及 entity-extractor 输出的 roles、systems、data_objects、triggers 逐项对照，输出覆盖度评分、已覆盖项、缺失项及改进建议。

**输入**：bpmn_xml、original_intent、original_entities。**输出**：coverage_score、covered_items、missing_items、recommendations。详见 `api-reference.md`。

仅做意图对齐评估，不修改工作流。与 bpmn-compliance-validator 并列，后者负责结构/逻辑校验。
