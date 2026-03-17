# BPMN Compliance Validator · 能力概述

对 BPMN 2.0 XML 进行结构合规性与逻辑一致性校验。结构检查包括命名空间、必要元素、ID 唯一性、引用有效性；逻辑检查包括孤立节点、死端、网关配置、死锁模式。

**输入**：bpmn_xml。**输出**：valid、errors、warnings。详见 `api-reference.md`。

仅做校验并输出报告，不修改 XML。与 intent-coverage-evaluator 并列，后者负责意图覆盖度评估。
