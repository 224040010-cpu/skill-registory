# BPMN Compliance Validator · 输入输出 Schema

## 输入

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bpmn_xml | string | 是 | BPMN 2.0 XML 字符串 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| valid | boolean | 是否通过校验（无 error 级问题） |
| errors | ValidationError[] | 错误列表 |
| warnings | ValidationWarning[] | 警告列表 |

## ValidationError / ValidationWarning 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 错误码（如 LOGIC_001、STRUCT_002） |
| severity | string | "error" 或 "warning" |
| message | string | 人类可读描述 |
| element_id | string | 可选，问题元素 id |

## 校验项与错误码

| 错误码 | 类型 | 说明 |
|--------|------|------|
| STRUCT_001 | error | definitions 缺少必要 xmlns |
| STRUCT_002 | warning | exclusiveGateway 出边缺少 conditionExpression |
| STRUCT_003 | error | 缺少 startEvent 或 endEvent |
| STRUCT_004 | error | flowNode ID 重复 |
| STRUCT_005 | error | sequenceFlow 引用无效 flowNode |
| STRUCT_006 | error | participant processRef 引用无效 process |
| LOGIC_001 | error | 节点不可达（孤立节点） |
| LOGIC_002 | error | 节点无法到达 endEvent（死端） |
| LOGIC_003 | error | exclusiveGateway 出边少于 2 条 |
| LOGIC_004 | error | parallelGateway fork 无匹配 join |
| LOGIC_005 | error | 死锁模式 |

输出后由编排层根据 valid 决定是否交付或回退修复。
