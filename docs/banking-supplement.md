# 银行行业补充内容 — 模板、规则与示例

> **配套文档**：《Skill Registry 银行行业迁移与维护指南》  
> **用途**：提供银行场景下 SKILL.md / TOOL.md 的标准模板、风险矩阵扩展、及完整示例  

---

## 目录

1. [银行 SKILL.md 标准模板](#一银行-skillmd-标准模板)
2. [银行 TOOL.md 标准模板](#二银行-toolmd-标准模板)
3. [银行风险矩阵扩展](#三银行风险矩阵扩展)
4. [数据分类与脱敏规则](#四数据分类与脱敏规则)
5. [示例 A：个人信贷审批 Skill](#五示例-a个人信贷审批-skill)
6. [示例 B：征信查询 Tool](#六示例-b征信查询-tool)
7. [示例 C：反洗钱名单筛查 Skill](#七示例-c反洗钱名单筛查-skill)
8. [银行术语敏感词库](#八银行术语敏感词库)

---

## 一、银行 SKILL.md 标准模板

```markdown
---
name: <kebab-case-skill-name>
bundle_scope: <bank-agent-name>         # e.g., credit-agent, risk-agent, compliance-agent
data_classification: <classification>    # public | internal | confidential | secret
consent_required: <true|false>          # true if customer data is involved
risk_level: <L0-L5>
regulatory_framework:
  - name: "<法规名称>"
    version: "<生效日期>"
    article: "<条款编号>"
description: |
  <一句话描述 Skill 的业务目的>
  Use when <精确触发条件，包含银行专业术语和典型用户表述>
  Do NOT use when <明确的不触发条件，防止路由污染>
---

# Purpose

<详细描述 Skill 解决的银行业务问题、业务价值、以及它在整个银行流程中的位置>

**前置条件**：
- <条件 1：如"客户已授权征信查询"、"用户已登录且具备审批权限">
- <条件 2>

**后置条件**：
- <条件 1：如"生成带审批意见的信贷申请记录"、"触发反洗钱预警工单">
- <条件 2>

---

# Trigger

**Use this Skill when:**
- <触发条件 1，含银行术语和典型口语表达>
- <触发条件 2>
- <触发条件 3>

**Do NOT use this Skill when:**
- <不触发条件 1，明确指向其他 Skill 的边界>
- <不触发条件 2>
- <不触发条件 3>

---

# Workflow

[ ] Step 1: <步骤描述>
    - Call `<mcp-server>:<tool_name>(param=value)` → <返回结果说明>
    - <校验/分支条件>

[ ] Step 2: <步骤描述>
    - Call `<mcp-server>:<tool_name>(param=value)` → <返回结果说明>
    - If <异常条件> → <异常处理：调用哪个 Tool 或如何上报>

[ ] Step N: <L4/L5 专用> 提交审批（如适用）
    - Call `approval-mcp:request_approval(level=1, ...)`
    - If APPROVED → proceed to Step N+1
    - If REJECTED → return rejection reason, stop
    - If ESCALATE → trigger level-2 approval

[ ] Step N+1: <执行核心操作>
    - Call `<mcp-server>:<tool_name>(...)`
    - Record `audit_trace_id` with every call

[ ] Step N+2: <验证与审计>
    - Call `audit-mcp:record_operation(trace_id, ...)`
    - Verify result integrity

---

# Constraints

- NEVER output raw PII in any response — apply `data-masking-mcp` before output
- ALWAYS obtain explicit consent before querying credit bureau or customer data
- NEVER store customer data in Skill context across sessions — ephemeral only
- ALWAYS route L4/L5 operations through the multi-level approval gate
- NEVER bypass the Verify Gate for any operation involving funds or customer accounts
- ALWAYS include `audit_trace_id` in every Tool call for regulatory traceability
- NEVER perform cross-customer data comparison without anonymization
- ALWAYS validate data classification before transmitting or storing any output
- NEVER make decisions on creditworthiness without outputting decision rationale
- ALWAYS respect `consent_required` flag — if consent is absent, abort and request it

---

# Input / Output Contract

## Input

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `<field1>` | `string` | 是 | <说明> | <示例> |
| `<field2>` | `object` | 否 | <说明> | <示例> |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| `result` | `object` | <业务结果> |
| `compliance_metadata` | `object` | <审计元数据，必须包含 audit_trace_id> |

---

# Error Handling

| 错误码 | 触发条件 | 处理建议 | 重试 |
|--------|---------|---------|------|
| `UNAUTHORIZED` | 用户权限不足 | 拒绝操作，返回所需权限说明 | 否 |
| `CONSENT_MISSING` | 客户未授权 | 请求客户授权后重试 | 是 |
| `APPROVAL_REJECTED` | 审批被拒绝 | 返回拒绝原因，终止流程 | 否 |
| `DATA_MASKING_FAILURE` | 脱敏失败 | 上报安全事件，拒绝输出 | 否 |
| `AUDIT_LOG_FAILURE` | 审计日志写入失败 | 记录到备用日志，上报运维 | 是 |
| `SYSTEM_ERROR` | 核心银行系统异常 | 触发回滚，上报值班 | 是（3次） |

---

# Examples

### Example 1: 正常流程

**Input:**
```json
{ "<field1>": "<value>", "audit_trace_id": "txn-20260702-uuid" }
```

**Expected Output:**
```json
{
  "result": { "<key>": "<value>" },
  "compliance_metadata": {
    "audit_trace_id": "txn-20260702-uuid",
    "operator_id": "user-12345",
    "operation_timestamp": "2026-07-02T10:00:00Z",
    "data_classification": "confidential",
    "approvers": [{ "level": 1, "approver_id": "mgr-001", "approval_time": "2026-07-02T09:58:00Z" }]
  }
}
```

### Example 2: 边界条件

<描述一个边界场景及预期处理>

### Example 3: 错误场景

<描述一个错误场景及预期输出>
```

---

## 二、银行 TOOL.md 标准模板

```yaml
tool_name: <kebab-case-verb-noun>
display_name: <Human Readable Name>
description: >
  <单行或折叠描述，说明 Tool 的原子操作，不超过 120 字符>
  <严禁包含编排、条件、多步逻辑词汇>

category: <parsing | transformation | validation | execution | retrieval | computation>

risk:
  level: <L0-L5>
  side_effects: <none | read | write | external>
  idempotent: <true | false>
  requires_approval: <true | false>   # 必须声明：L4/L5 必须为 true

ownership:
  team: <owner-team>
  service: <mcp-server-name>

data_classification:
  input: <public | internal | confidential | secret>
  output: <public | internal | confidential | secret>
  retention_days: <365 | 1825 | 5475>  # 1年 / 5年 / 15年

input_schema:
  type: object
  required:
    - <field1>
    - audit_trace_id
  properties:
    <field1>:
      type: <string | number | boolean | object | array>
      description: >
        <字段说明，包含格式要求、取值范围、校验规则>
    audit_trace_id:
      type: string
      description: "UUID，贯穿整个请求链路，用于审计追溯"
      format: uuid

output_schema:
  type: object
  properties:
    result:
      type: object
      description: "业务结果"
    compliance_metadata:
      type: object
      required:
        - audit_trace_id
        - operation_timestamp
      properties:
        audit_trace_id:
          type: string
          description: "UUID，与输入一致"
        operation_timestamp:
          type: string
          format: date-time
          description: "ISO 8601 时间戳"

errors:
  - code: INVALID_INPUT
    message: "Input parameter failed validation — check schema and re-submit"
    retryable: false
  - code: UNAUTHORIZED
    message: "Caller lacks permission for this operation"
    retryable: false
  - code: CONSENT_MISSING
    message: "Required customer consent not found or expired"
    retryable: true
  - code: SYSTEM_ERROR
    message: "Downstream system error — retry with exponential backoff"
    retryable: true
  - code: AUDIT_FAILURE
    message: "Audit log write failed — operation was executed but not logged"
    retryable: false

called_by_skills:
  - <skill-name-1>
  - <skill-name-2>

regulatory_notes: >
  <如有监管特殊要求，在此说明。例如：>
  <"本工具查询的数据来源于央行征信中心，调用方必须持有客户书面授权">
  <"输出数据保留期限为 5 年，超出后自动删除">
```

---

## 三、银行风险矩阵扩展

原矩阵（充电桩场景）与银行扩展矩阵对比：

| 等级 | 原名称 | 原 side_effects | 银行扩展名称 | 银行扩展 side_effects | 是否需要审批 |
|------|--------|----------------|-------------|---------------------|------------|
| L0 | — | — | 纯查询 | none | 否 |
| L1 | Read-only | read | 客户信息查询 | read | 否（但需登录权限） |
| L2 | Analysis | read | 分析与报告 | read | 否 |
| L3 | Write / Create | write | 写操作/通知 | write | 是（一级） |
| L4 | Device Control | external | 资金操作 | external | 是（两级） |
| L5 | — | — | 监管操作 | external | 是（两级 + 合规确认） |

**风险等级与数据分类交叉矩阵**：

| 数据分类 / 风险等级 | L0 | L1 | L2 | L3 | L4 | L5 |
|---------------------|----|----|----|----|----|----|
| public | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| internal | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| confidential | ✅ | ✅ | ⚠️ | ❌需脱敏 | ❌需脱敏 | ❌需脱敏 |
| secret | ✅ | ✅ | ❌需审批 | ❌需审批+脱敏 | ❌需审批+脱敏 | ❌需审批+脱敏 |

---

## 四、数据分类与脱敏规则

### 4.1 数据分类标准

| 等级 | 定义 | 银行示例 | 脱敏要求 | 保留期限 |
|------|------|---------|---------|---------|
| **public** | 公开数据，无泄露风险 | 基准利率、汇率、产品公示利率 | 无需脱敏 | 1年 |
| **internal** | 内部运营数据，泄露影响有限 | 网点运营数据、内部报表（不含客户信息） | 内部传输无需脱敏 | 3年 |
| **confidential** | 客户敏感数据，泄露影响较大 | 客户姓名、账户余额、交易明细、征信报告 | 必须脱敏 | 5年 |
| **secret** | 核心商业秘密/国家金融数据，泄露影响重大 | 风控模型参数、监管内部通报、反洗钱线索 | 严格脱敏+加密 | 15年 |

### 4.2 脱敏规则速查表

| 数据类型 | 脱敏规则 | 脱敏前 | 脱敏后 |
|---------|---------|--------|--------|
| 客户姓名 | 保留姓，名替换为 * | 张三 | 张* |
| 身份证号 | 前3位 + **** + 后4位 | 110101199001011234 | 110***********1234 |
| 银行卡号 | 前6位 + ****** + 后4位 | 6222021234567890123 | 622202******0123 |
| 手机号 | 前3位 + **** + 后4位 | 13812345678 | 138****5678 |
| 交易金额 | 精确到万位 + 模糊后缀 | ¥1,234,567.89 | ~¥123万 |
| 邮箱地址 | 用户名部分脱敏 + 域名保留 | zhangsan@bank.com | z***@bank.com |
| 地址 | 保留到区县，后续脱敏 | 北京市朝阳区建国路88号 | 北京市朝阳区*** |
| 企业名称 | 保留关键词 + 行业脱敏 | 某某科技有限公司 | 某某***公司 |
| 征信报告摘要 | 仅保留评分段，删除明细 | 评分720，含3条逾期记录 | 评分720，含逾期记录（N条） |

### 4.3 脱敏 Tool 调用规范

```
# 标准脱敏调用链（嵌入任何输出客户数据的 Skill 中）

[ ] Step: 数据脱敏
    - Call `data-masking-mcp:mask_sensitive_data(
        data=<raw_output>,
        level="PII",            # PII | PCI | FULL
        preserve_structure=true # 保持 JSON 结构不变
      )` → masked_data
    - Verify no raw PII remains in masked_data
    - If masking fails → abort, return `DATA_MASKING_FAILURE`
```

---

## 五、示例 A：个人信贷审批 Skill

### 完整 SKILL.md

```markdown
---
name: approving-personal-mortgage
bundle_scope: credit-agent
data_classification: confidential
consent_required: true
risk_level: L4
regulatory_framework:
  - name: "个人贷款管理暂行办法"
    version: "2010-02-12"
    article: "第7-12条"
  - name: "征信业管理条例"
    version: "2013-03-15"
    article: "第13-20条"
description: |
  处理个人住房按揭贷款申请的完整审批流程：从客户信息核验、征信查询、额度评估、利率定价到最终审批决策，输出带审批意见的信贷申请记录。
  Use when the user submits a personal mortgage loan application, requests credit assessment, or says "申请房贷"、"审批按揭贷款"、"评估贷款额度"、"个人住房贷款申请".
  Do NOT use when the user only wants to calculate mortgage payment schedules — use mortgage-calculator instead.
  Do NOT use when the application is for corporate/business loans — use approving-corporate-credit instead.
---

# Purpose

End-to-end orchestration skill for personal mortgage loan approval. Validates
applicant identity, queries credit bureau, assesses repayment capacity,
calculates loan limit and interest rate, and produces a structured approval
verdict with full decision rationale.

**前置条件**：
- 客户已提交完整贷款申请资料（身份证明、收入证明、购房合同）
- 客户已签署征信查询授权书
- 操作人员具备信贷审批权限

**后置条件**：
- 生成带审批意见的信贷申请记录
- 若审批通过，生成合同草案并进入签约流程
- 若审批拒绝，生成拒绝原因说明并通知客户

---

# Trigger

**Use this Skill when:**
- User submits a personal mortgage application with required documents
- User says "申请房贷"、"审批按揭贷款"、"评估贷款额度"、"个人住房贷款申请"
- User provides applicant income, property value, and down payment ratio
- Orchestrator needs to process a complete mortgage approval pipeline

**Do NOT use this Skill when:**
- User only wants to calculate monthly payment — use `mortgage-calculator`
- User wants to check existing application status — use `querying-loan-status`
- Application is for corporate/business loans — use `approving-corporate-credit`
- User has not provided income proof or property contract — request documents first

---

# Workflow

[ ] Step 1: 验证客户身份与授权
    - Call `kyc-aml-mcp:verify_identity(id_number, name, phone)` → identity_verified
    - Call `kyc-aml-mcp:check_consent(customer_id, consent_type="credit_query")` → consent_status
    - If consent_status != "GRANTED" → return CONSENT_MISSING error, stop
    - Call `audit-mcp:record_step(trace_id, step="identity_verification")`

[ ] Step 2: 查询征信报告
    - Call `credit-mcp:query_credit_report(customer_id, purpose="mortgage_approval")` → credit_report
    - Extract credit_score, total_debt, overdue_count, recent_inquiry_count
    - If credit_score < 600 or overdue_count > 2 → flag HIGH_RISK
    - Call `audit-mcp:record_step(trace_id, step="credit_query")`

[ ] Step 3: 计算还款能力与额度
    - Call `credit-risk-mcp:calculate_debt_ratio(
        monthly_income, total_monthly_debt, proposed_monthly_payment)` → dti_ratio
    - Call `credit-risk-mcp:assess_loan_limit(
        property_value, down_payment_ratio, monthly_income, credit_score)` → max_loan_amount
    - If dti_ratio > 0.5 → flag CAPACITY_INSUFFICIENT
    - Call `audit-mcp:record_step(trace_id, step="capacity_assessment")`

[ ] Step 4: 利率定价
    - Call `core-banking-mcp:query_rate_matrix(
        loan_type="mortgage", credit_score, loan_term_years, ltv_ratio)` → interest_rate
    - Call `audit-mcp:record_step(trace_id, step="rate_pricing")`

[ ] Step 5: 生成审批意见书
    - Call `credit-risk-mcp:generate_approval_memo(
        customer_id, credit_score, dti_ratio, max_loan_amount, interest_rate, risk_flags)` → memo
    - Call `audit-mcp:record_step(trace_id, step="memo_generation")`

[ ] Step 6: 提交审批（L4 操作）
    - Call `approval-mcp:request_approval(
        level=1, operation="mortgage_approval", params={memo}, requester_id)` → level1_result
    - If level1_result == "ESCALATE" → call `approval-mcp:request_approval(level=2, ...)` → level2_result
    - If any rejection → return rejection with reason, stop
    - Call `audit-mcp:record_step(trace_id, step="approval", approvers=[...])`

[ ] Step 7: 执行审批决策
    - If APPROVED → call `core-banking-mcp:create_loan_record(customer_id, loan_amount, rate, term)` → loan_record
    - If REJECTED → call `core-banking-mcp:record_rejection(customer_id, reason)` → rejection_record
    - Call `audit-mcp:record_operation(trace_id, operation="mortgage_decision", result, approvers=[...])`

[ ] Step 8: 脱敏输出
    - Call `data-masking-mcp:mask_sensitive_data(result, level="PII")` → masked_result
    - Verify no raw PII remains
    - Return masked_result with compliance_metadata

---

# Constraints

- NEVER output raw PII in any response — always apply masking before output
- ALWAYS obtain explicit consent before querying credit bureau data
- NEVER store customer credit data in Skill context across sessions
- ALWAYS route L4 operations through the multi-level approval gate
- NEVER bypass the Verify Gate for any operation involving loan funds
- ALWAYS include `audit_trace_id` in every Tool call
- NEVER make credit decisions without outputting full decision rationale
- ALWAYS validate `consent_required` flag — if consent is absent, abort
- NEVER approve loans where dti_ratio > 0.5 without exceptional override
- ALWAYS check AML sanctions list before any loan approval

---

# Input / Output Contract

## Input

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `customer_id` | `string` | 是 | 客户唯一标识 |
| `id_number` | `string` | 是 | 身份证号（18位） |
| `name` | `string` | 是 | 客户姓名 |
| `phone` | `string` | 是 | 手机号 |
| `monthly_income` | `number` | 是 | 月收入（元） |
| `property_value` | `number` | 是 | 房产评估价值（元） |
| `down_payment_ratio` | `number` | 是 | 首付比例（0.0-1.0） |
| `loan_term_years` | `integer` | 是 | 贷款期限（年） |
| `audit_trace_id` | `string` | 是 | 审计追踪 ID |

## Output

| 字段 | 类型 | 说明 |
|------|------|------|
| `decision` | `string` | `APPROVED` / `REJECTED` / `CONDITIONAL` |
| `loan_amount` | `number` | 批准贷款金额（元） |
| `interest_rate` | `number` | 年化利率（%） |
| `monthly_payment` | `number` | 月供金额（元） |
| `decision_rationale` | `string` | 决策依据说明 |
| `risk_flags` | `array` | 风险标记列表 |
| `compliance_metadata` | `object` | 审计元数据 |

---

# Error Handling

| 错误码 | 触发条件 | 处理 | 重试 |
|--------|---------|------|------|
| `CONSENT_MISSING` | 客户未授权征信查询 | 请求授权后重试 | 是 |
| `IDENTITY_MISMATCH` | 身份信息核验失败 | 要求重新提供证件 | 否 |
| `AML_HIT` | 反洗钱名单命中 | 立即冻结，上报合规 | 否 |
| `CAPACITY_INSUFFICIENT` | 还款能力不足 | 降低额度或拒绝 | 否 |
| `APPROVAL_REJECTED` | 审批被驳回 | 返回驳回原因 | 否 |
| `SYSTEM_ERROR` | 核心银行系统异常 | 回滚，上报值班 | 是（3次） |

---

# Examples

### Example 1: 标准审批通过

**Input:**
```json
{
  "customer_id": "C-20260702-001",
  "id_number": "110101199001011234",
  "name": "张三",
  "phone": "13812345678",
  "monthly_income": 30000,
  "property_value": 5000000,
  "down_payment_ratio": 0.35,
  "loan_term_years": 30,
  "audit_trace_id": "txn-20260702-abc123"
}
```

**Expected Output:**
```json
{
  "decision": "APPROVED",
  "loan_amount": 3250000,
  "interest_rate": 3.85,
  "monthly_payment": 15200,
  "decision_rationale": "客户信用评分720（良好），无逾期记录，DTI比率0.45（符合标准），LTV比率65%（低于70%警戒线），符合首套房按揭贷款审批条件。",
  "risk_flags": [],
  "compliance_metadata": {
    "audit_trace_id": "txn-20260702-abc123",
    "operator_id": "user-credit-001",
    "operation_timestamp": "2026-07-02T10:30:00Z",
    "data_classification": "confidential",
    "approvers": [
      { "level": 1, "approver_id": "mgr-credit-001", "approval_time": "2026-07-02T10:28:00Z" }
    ]
  }
}
```

### Example 2: 信用评分不足拒绝

**Input:** 同上，但 credit_score = 580, overdue_count = 3

**Expected Output:**
```json
{
  "decision": "REJECTED",
  "loan_amount": 0,
  "decision_rationale": "客户信用评分580（低于600分门槛），且存在3笔逾期记录，不满足我行个人住房贷款准入标准。建议6个月后重新申请。",
  "risk_flags": ["CREDIT_SCORE_LOW", "MULTIPLE_OVERDUES"],
  "compliance_metadata": {
    "audit_trace_id": "txn-20260702-abc123",
    "operator_id": "user-credit-001",
    "operation_timestamp": "2026-07-02T10:30:00Z",
    "data_classification": "confidential",
    "approvers": [
      { "level": 1, "approver_id": "mgr-credit-001", "approval_time": "2026-07-02T10:28:00Z" }
    ]
  }
}
```
```

---

## 六、示例 B：征信查询 Tool

```yaml
tool_name: query-credit-bureau
display_name: Query Credit Bureau Report
description: >
  Queries the People's Bank of China credit bureau for a customer's credit report.
  Requires valid customer consent and authorization. Returns credit score, debt summary,
  overdue history, and inquiry records. Output is pre-masked for PII.

category: retrieval

risk:
  level: L1
  side_effects: read
  idempotent: true
  requires_approval: false

ownership:
  team: credit-risk
  service: credit-mcp

data_classification:
  input: confidential
  output: confidential
  retention_days: 1825  # 5 years

input_schema:
  type: object
  required:
    - customer_id
    - id_number
    - consent_reference
    - audit_trace_id
  properties:
    customer_id:
      type: string
      description: "银行内部客户唯一标识"
    id_number:
      type: string
      description: "客户身份证号（18位），用于征信中心查询"
      pattern: "^[0-9]{17}[0-9X]$"
    consent_reference:
      type: string
      description: "客户签署的征信查询授权书编号"
    purpose:
      type: string
      enum: [mortgage_approval, credit_card, personal_loan, corporate_loan, review]
      description: "查询用途，必须与客户授权书中的用途一致"
    audit_trace_id:
      type: string
      format: uuid
      description: "审计追踪 ID，贯穿整个请求链路"

output_schema:
  type: object
  properties:
    credit_score:
      type: integer
      description: "央行征信评分（350-950）"
      minimum: 350
      maximum: 950
    total_debt:
      type: number
      description: "客户总负债（元），已脱敏为万位"
    overdue_count:
      type: integer
      description: "历史逾期笔数"
    recent_inquiry_count:
      type: integer
      description: "近6个月征信查询次数"
    credit_summary:
      type: string
      description: "信用状况摘要（已脱敏）"
    compliance_metadata:
      type: object
      properties:
        audit_trace_id:
          type: string
        operation_timestamp:
          type: string
          format: date-time
        data_source:
          type: string
          description: "数据源：央行征信中心"
        retention_until:
          type: string
          format: date
          description: "数据保留截止日期"

errors:
  - code: INVALID_INPUT
    message: "身份证号格式错误或 consent_reference 无效"
    retryable: false
  - code: CONSENT_MISSING
    message: "客户未授权或授权已过期"
    retryable: true
  - code: UNAUTHORIZED
    message: "调用方无征信查询权限"
    retryable: false
  - code: CREDIT_BUREAU_ERROR
    message: "征信中心服务不可用"
    retryable: true
  - code: AUDIT_FAILURE
    message: "审计日志写入失败"
    retryable: false

called_by_skills:
  - approving-personal-mortgage
  - approving-corporate-credit
  - credit-card-application
  - reviewing-credit-exposure

regulatory_notes: >
  本工具查询的数据来源于中国人民银行征信中心。
  调用方必须持有客户书面签署的《个人信用报告查询授权书》，
  且查询用途必须与授权书中声明的用途一致。
  输出数据保留期限为 5 年，超出后自动删除。
  任何未经授权的查询将被视为违规操作，触发合规告警。
```

---

## 七、示例 C：反洗钱名单筛查 Skill

### 简化版 SKILL.md

```markdown
---
name: screening-aml-sanctions
bundle_scope: compliance-agent
data_classification: secret
consent_required: false
risk_level: L2
regulatory_framework:
  - name: "反洗钱法"
    version: "2021-01-01"
    article: "第16-20条"
  - name: "金融机构反洗钱规定"
    version: "2006-11-14"
    article: "第15-18条"
description: |
  对客户、交易对手或实体进行反洗钱名单筛查，覆盖联合国制裁名单、OFAC、欧盟制裁名单、中国公安部涉恐名单、PEP（政治公众人物）名单等。
  Use when onboarding a new customer, processing a large transaction (>50k USD), or the user says "反洗钱筛查"、"制裁名单检查"、"AML check"、"PEP screening".
  Do NOT use when the user only wants to check domestic court records — use querying-court-records instead.
---

# Purpose

Screens names, entities, and transactions against global sanctions and
AML watchlists. Returns match confidence, match type, and recommended action.

---

# Workflow

[ ] Step 1: 解析筛查对象
    - Call `kyc-aml-mcp:parse_screening_target(name, id_number, entity_type)` → target

[ ] Step 2: 多名单并行筛查
    - Call `kyc-aml-mcp:screen_un_list(target)` → un_match
    - Call `kyc-aml-mcp:screen_ofac(target)` → ofac_match
    - Call `kyc-aml-mcp:screen_cn_mps(target)` → cn_mps_match
    - Call `kyc-aml-mcp:screen_pep(target)` → pep_match

[ ] Step 3: 综合评估
    - Call `kyc-aml-mcp:assess_match_risk([un_match, ofac_match, cn_mps_match, pep_match])` → risk_assessment
    - If risk_assessment.level == "HIGH" → trigger `compliance-mcp:freeze_alert(target)`
    - Call `audit-mcp:record_operation(trace_id, operation="aml_screening", result=risk_assessment)`

[ ] Step 4: 脱敏输出
    - Call `data-masking-mcp:mask_sensitive_data(risk_assessment, level="FULL")` → masked_result
    - Return masked_result with compliance_metadata

---

# Constraints

- NEVER disclose the full details of sanctions list matches to unauthorized personnel
- ALWAYS escalate HIGH risk matches to compliance officer within 15 minutes
- NEVER clear a HIGH risk alert without senior compliance approval
- ALWAYS record screening results in the immutable audit trail
- NEVER perform batch screening without prior approval from compliance head

---

# Input / Output

## Input
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `string` | 是 | 待筛查姓名或实体名 |
| `id_number` | `string` | 否 | 身份证号/护照号 |
| `entity_type` | `string` | 是 | `individual` / `corporate` |
| `transaction_amount` | `number` | 否 | 交易金额（触发大额筛查） |
| `audit_trace_id` | `string` | 是 | 审计追踪 ID |

## Output
| 字段 | 类型 | 说明 |
|------|------|------|
| `screening_result` | `string` | `CLEAR` / `MATCH` / `PENDING_REVIEW` |
| `match_details` | `array` | 匹配详情列表（已脱敏） |
| `recommended_action` | `string` | 建议动作 |
| `compliance_metadata` | `object` | 审计元数据 |
```

---

## 八、银行术语敏感词库

用于 `admission_gate.py` 的"路由治理检查"和 `validate_skill.py` 的模糊词检测。

### 8.1 模糊词（被标记为 WARNING）

```python
BANKING_VAGUE_WORDS = [
    "处理",        # 过于宽泛，无法路由
    "查询",        # 需明确查询什么
    "管理",        # 管理什么？
    "操作",        # 什么操作？
    "办理业务",    # 什么业务？
    "处理贷款",    # 哪种贷款？什么流程？
    "查询客户",    # 查询客户什么？
    "查看数据",    # 什么数据？
    "报送信息",    # 报送给谁？什么信息？
    "处理交易",    # 什么交易？查询还是执行？
    "风险分析",    # 信用风险？市场风险？操作风险？
]
```

### 8.2 高风险触发词（被标记为 REQUIRES_REVIEW）

```python
BANKING_HIGH_RISK_TRIGGERS = {
    "资金": { "min_risk_level": "L3", "reason": "涉及资金操作需至少 L3" },
    "转账": { "min_risk_level": "L4", "reason": "资金转移必须 L4 及以上" },
    "放款": { "min_risk_level": "L4", "reason": "贷款发放涉及资金变动" },
    "扣款": { "min_risk_level": "L4", "reason": "扣款操作必须 L4" },
    "开卡": { "min_risk_level": "L4", "reason": "账户开立涉及客户身份与资金" },
    "销户": { "min_risk_level": "L4", "reason": "账户注销涉及资金清算" },
    "征信报送": { "min_risk_level": "L5", "reason": "监管报送必须 L5" },
    "反洗钱": { "min_risk_level": "L2", "reason": "AML 涉及秘密数据" },
    "跨境": { "min_risk_level": "L5", "reason": "跨境数据/资金需 L5" },
    "监管报送": { "min_risk_level": "L5", "reason": "监管报送必须 L5" },
}
```

### 8.3 建议的 SKILL.md 命名规范（银行）

```
<verb>-<banking-domain>-<object>

动词（动词原形）：
  approving, rejecting, querying, screening, calculating, generating,
  validating, reporting, freezing, alerting, reviewing, assessing

银行领域：
  personal-mortgage, corporate-credit, credit-card, aml-sanctions,
  regulatory-reporting, kyc, customer-service, wealth-management

对象：
  application, transaction, customer, report, alert, limit, rate, portfolio

示例：
  approving-personal-mortgage-application
  querying-corporate-credit-limit
  screening-aml-sanctions-list
  generating-regulatory-reporting-csv
  assessing-wealth-management-portfolio
```

---

*本文件为银行行业迁移配套文档，应与《迁移与维护指南》配套使用。*
