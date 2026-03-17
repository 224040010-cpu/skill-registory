# BPMN 模板匹配 · 能力概述

用结构化意图检索 BPMN 模板库，输出候选模板及相似度。仅做检索与打分，不修改模板、不定制步骤。编排层根据 best_match 决定直接采用模板或走 process-decomposer。

**输入**：结构化意图（intent-parser 输出）。**输出**：candidates（template_id, template_name, similarity_score, description）、best_match。详见 `api-reference.md`。
