---
name: bpmn-compliance-validator
description: Validates BPMN XML for both structural compliance (BPMN 2.0 schema) and logical consistency (no deadlocks, no orphan nodes, no data breaks). Combined structural and logical validation in one pass. Only validates, does not modify. Use when BPMN validation, 校验BPMN, 验证XML, or 合规检查.
---

# BPMN Compliance Validator

对 BPMN 2.0 XML 做结构合规性校验（命名空间、必要元素）和逻辑一致性检查（死锁、孤立节点、数据断链），输出校验报告。合并 schema 校验与逻辑检查为单次校验。仅做校验，不修改 XML。

## Trigger

**Use this Skill when:**
- 处于 business-to-bpmn 验证层，BPMN XML 已生成，需要校验
- 用户明确要求「BPMN 校验」「验证 XML」「合规检查」

**Do NOT use this Skill when:**
- 需要评估意图覆盖度（用 intent-coverage-evaluator）
- 需要修改 XML（用 bpmn-diagram-optimizer 或 bpmn-xml-serializer）

## Instructions

### Structural Checks

1. definitions root has required xmlns declarations
2. At least one startEvent exists in each process
3. At least one endEvent exists in each process
4. All flowNode IDs are unique
5. All sequenceFlow sourceRef/targetRef reference valid flowNode IDs
6. Participant processRef references valid process IDs

### Logical Checks

7. All flowNodes are reachable from a startEvent (no orphan nodes)
8. All flowNodes can reach an endEvent (no dead ends)
9. ExclusiveGateway has at least 2 outgoing sequenceFlows
10. ParallelGateway fork has matching join
11. No deadlock patterns (mutually exclusive gateways blocking each other)
12. sequenceFlows from exclusiveGateway should have conditionExpressions (except default flow)

## Input

| 字段 | 类型 | 说明 |
|------|------|------|
| bpmn_xml | string | BPMN 2.0 XML 字符串 |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| valid | boolean | 是否通过校验 |
| errors | ValidationError[] | 错误列表 |
| warnings | ValidationWarning[] | 警告列表 |

**ValidationError:** `{ code: string, severity: "error"|"warning", message: string, element_id?: string }`

## Example

**Input:**
```json
{
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

**Output (with orphan node):**
```json
{
  "valid": false,
  "errors": [
    {
      "code": "LOGIC_001",
      "severity": "error",
      "message": "Node Element_7 is not reachable from any startEvent",
      "element_id": "Element_7"
    }
  ],
  "warnings": [
    {
      "code": "STRUCT_002",
      "severity": "warning",
      "message": "ExclusiveGateway Element_4 has outgoing flow without conditionExpression",
      "element_id": "Element_4"
    }
  ]
}
```

**Output (valid):**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

## References

- 能力概述：See `references/overview.md`
- I/O Schema：See `references/api-reference.md`

## Constraints

- 仅做校验，不修改 XML
- severity 为 "error" 时 valid 为 false；仅 "warning" 时 valid 可为 true
