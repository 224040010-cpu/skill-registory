# business-to-bpmn 概述

## 定位

将用户自然语言业务描述**直接**转化为 BPMN 2.0 标准工作流 XML。与现有方案的区别：

| 方案 | 路径 | Skill 数量 | 中间格式 |
|------|------|-----------|---------|
| workflow-from-business | 业务 → JSON/YAML | 13 | 无 |
| flowchart-to-bpmn | Mermaid → BPMN XML | 14 | Mermaid |
| **business-to-bpmn** | **业务 → BPMN XML** | **15** | **无** |

## 5 层架构

### Layer 1: 理解层 (Understanding)
解析用户自然语言，提取结构化意图、关键实体，识别歧义。

| Skill | 职责 | 原子性边界 |
|-------|------|-----------|
| intent-parser | 语义理解 → 结构化意图 | 不做决策或规划 |
| entity-extractor | 实体识别 → 角色/系统/数据/触发器 | 不做关联推理 |
| ambiguity-detector | 歧义检测 → 澄清问题 | 不替用户假设 |

### Layer 2: 规划层 (Planning)
将业务目标拆解为 BPMN-aware 的步骤序列，计算依赖关系。

| Skill | 职责 | 原子性边界 |
|-------|------|-----------|
| bpmn-template-matcher | 模板检索与匹配 | 不修改模板 |
| process-decomposer | 步骤拆分（含 BPMN 元素提示） | 不生成 DAG |
| dependency-resolver | DAG 依赖计算 | 不做并行优化 |
| parallel-optimizer | 并行可行性分析 | 不改依赖关系 |

### Layer 3: BPMN 建模层 (BPMN Modeling)
将步骤映射为 BPMN 2.0 元素，构建完整的流程模型。

| Skill | 职责 | 原子性边界 |
|-------|------|-----------|
| bpmn-element-mapper | 步骤 → BPMN 元素类型 | 不决定 task 子类型 |
| bpmn-task-classifier | 确定 userTask/serviceTask/scriptTask | 不修改其他元素 |
| bpmn-model-assembler | 组装 process 模型（nodes + flows） | 不处理泳道/消息流 |
| bpmn-participant-organizer | 分配泳道、池、消息流 | 不修改流程逻辑 |

### Layer 4: BPMN 渲染层 (BPMN Rendering)
序列化为 XML 并执行视觉优化。

| Skill | 职责 | 原子性边界 |
|-------|------|-----------|
| bpmn-xml-serializer | 生成 BPMN 2.0 XML + BPMNDI | 不做校验 |
| bpmn-diagram-optimizer | 布局 + 样式 + 标签优化 | 不修改流程逻辑 |

### Layer 5: 验证层 (Validation)
校验结构合规性和业务覆盖度。

| Skill | 职责 | 原子性边界 |
|-------|------|-----------|
| bpmn-compliance-validator | 结构 + 逻辑校验 | 不修改 XML |
| intent-coverage-evaluator | 意图覆盖度评估 | 不修改工作流 |

## 编排策略

1. **分层流水线**：Layer 1 → 2 → 3 → 4 → 5 严格顺序
2. **澄清循环**：ambiguity-detector 返回问题时暂停，用户回答后重跑理解层
3. **模板快捷路径**：bpmn-template-matcher 高匹配时跳过 process-decomposer / dependency-resolver / parallel-optimizer
4. **验证回退**：验证不通过时回到对应层修正，仅重跑该层及后续
5. **单节点迭代**：bpmn-element-mapper 对每个步骤独立映射
