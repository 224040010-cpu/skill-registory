# 异常处理与常见问题

## 常见问题

### Q1: 理解层返回空意图
**原因**: 用户输入过于简短或缺乏业务上下文
**处理**: ambiguity-detector 应生成引导性问题（如"请描述流程的触发条件"），返回用户获取更多信息

### Q2: 模板匹配分数在 0.5-0.8 之间
**处理**: 以最高分模板为参考骨架，但仍走 process-decomposer 路径进行定制化拆解。模板仅作为步骤拆解的提示输入，不直接使用

### Q3: DAG 出现环路
**原因**: 业务流程含回环（如"审批不通过退回修改"）
**处理**: dependency-resolver 应将回环标注为 `loop_back` 类型边，在 BPMN 中映射为 sequenceFlow 回连，不视为依赖冲突

### Q4: 验证层报告孤立节点
**原因**: bpmn-model-assembler 遗漏了某些 sequenceFlow
**处理**: 回到 Layer 3 的 bpmn-model-assembler，检查 DAG 中所有 edge 是否都已转为 sequenceFlow

### Q5: 意图覆盖度评分低 (< 0.7)
**原因**: 规划层拆解遗漏了部分业务步骤
**处理**: 回到 Layer 2 的 process-decomposer，将 missing_items 作为补充输入重新拆解

### Q6: BPMN XML 在 bpmn.io 中无法打开
**原因**: XML 命名空间或结构不符合 BPMN 2.0 schema
**处理**: 检查 bpmn-xml-serializer 输出的 definitions 根元素是否包含正确的 xmlns 声明

## 回退策略

| 验证错误类型 | 回退到 | 说明 |
|-------------|--------|------|
| XML 格式错误 | Layer 4: bpmn-xml-serializer | 重新序列化 |
| 孤立节点/断链 | Layer 3: bpmn-model-assembler | 补充缺失的 sequenceFlow |
| 任务类型错误 | Layer 3: bpmn-task-classifier | 重新分类 |
| 泳道分配错误 | Layer 3: bpmn-participant-organizer | 重新分配 |
| 步骤遗漏 | Layer 2: process-decomposer | 补充步骤 |
| 意图理解错误 | Layer 1: intent-parser | 重新解析 |
