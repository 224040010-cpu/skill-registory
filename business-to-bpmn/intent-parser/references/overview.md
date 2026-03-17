# Intent Parser · 能力概述

将用户自然语言描述解析为单一结构化意图对象，供后续 entity-extractor 与 ambiguity-detector 使用。

**职责边界**：仅做语义理解与结构化输出，不做业务决策、不选模板、不拆步骤、不生成 BPMN。

**输入**：`{ user_description: string }` — 用户自然语言业务描述。

**输出**：`{ business_type, goal, constraints, scope }` — 结构化意图 JSON。详见 `api-reference.md`。

**典型业务类型**：approval、data-sync、alert-handling、reporting、order-processing、ticket-routing 等。
